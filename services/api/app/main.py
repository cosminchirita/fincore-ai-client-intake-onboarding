import hashlib
import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import UUID

from fastapi import Depends, FastAPI, File, Header, HTTPException, Request, UploadFile, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError

from app.ai import PROMPT_VERSION, get_ai_provider
from app.config import get_settings
from app.db import close_pool, open_pool
from app.emailer import send_template
from app.repository import (
    create_lead,
    dashboard_kpis,
    get_document_count,
    get_idempotent_response,
    get_processed_event_lead,
    get_lead,
    list_dashboard_leads,
    record_workflow_error,
    save_document,
    save_idempotent_response,
    save_processing_result,
    update_lead_status,
)
from app.schemas import (
    EmailRequest,
    IntakeAccepted,
    IntakeCreate,
    StatusUpdate,
    WorkflowError,
)
from app.scoring import ScoringInput, score_lead
from app.security import (
    pseudonymize,
    require_dashboard_key,
    require_internal_key,
    safe_filename,
)

logging.basicConfig(level=get_settings().log_level)
logger = logging.getLogger("fincore-api")
BASE_DIR = Path(__file__).resolve().parent
TEMPLATES = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    open_pool()
    yield
    close_pool()


app = FastAPI(
    title="FinCore AI Client Intake API",
    version="0.1.0",
    description="Auditable AI-assisted intake and onboarding demo for accounting firms.",
    lifespan=lifespan,
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Cache-Control"] = "no-store"
    return response


def _audit_context(request: Request) -> dict[str, str | None]:
    client_ip = request.client.host if request.client else None
    return {
        "ip_hash": pseudonymize(client_ip),
        "user_agent_hash": pseudonymize(request.headers.get("user-agent")),
    }


def _accepted(lead: dict) -> dict:
    return IntakeAccepted(
        lead_id=lead["id"],
        correlation_id=lead["correlation_id"],
        status=lead["status"],
        message="Request received. Processing is asynchronous and subject to human review.",
    ).model_dump(mode="json")


@app.get("/health", tags=["operations"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "fincore-intake-api"}


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def intake_page(request: Request):
    return TEMPLATES.TemplateResponse(request=request, name="intake_form.html", context={})


@app.post("/api/v1/intake", response_model=IntakeAccepted, status_code=status.HTTP_202_ACCEPTED)
def create_intake(
    intake: IntakeCreate,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    payload = intake.model_dump(exclude={"website"}, mode="json")
    request_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    if idempotency_key:
        try:
            cached = get_idempotent_response(idempotency_key[:160], request_hash)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        if cached:
            _, body = cached
            return JSONResponse(status_code=202, content=body)

    lead = create_lead(intake, _audit_context(request))
    body = _accepted(lead)
    if idempotency_key:
        save_idempotent_response(idempotency_key[:160], request_hash, 202, body)
    return body


@app.post("/api/v1/intake/form", response_class=HTMLResponse, include_in_schema=False)
async def create_intake_form(request: Request):
    form = await request.form()
    try:
        payload = IntakeCreate(
            source="web_form",
            contact_name=str(form.get("contact_name", "")),
            company_name=str(form.get("company_name", "")),
            email=str(form.get("email", "")),
            phone=str(form.get("phone") or "") or None,
            country_code=str(form.get("country_code") or "RO"),
            industry=str(form.get("industry") or "") or None,
            employee_count=int(form["employee_count"]) if form.get("employee_count") else None,
            monthly_document_volume=(
                int(form["monthly_document_volume"]) if form.get("monthly_document_volume") else None
            ),
            annual_revenue_band=str(form.get("annual_revenue_band") or "unknown"),
            requested_services=[str(value) for value in form.getlist("requested_services")],
            urgency=str(form.get("urgency") or "normal"),
            message=str(form.get("message", "")),
            consent_privacy=form.get("consent_privacy") == "on",
            consent_marketing=form.get("consent_marketing") == "on",
            website=str(form.get("website", "")),
        )
    except (ValidationError, ValueError) as exc:
        return TEMPLATES.TemplateResponse(
            request=request,
            name="intake_form.html",
            context={"error": str(exc)},
            status_code=422,
        )
    lead = create_lead(payload, _audit_context(request))
    return TEMPLATES.TemplateResponse(
        request=request,
        name="intake_form.html",
        context={"success": True, "lead_id": str(lead["id"])},
        status_code=202,
    )


@app.post("/api/v1/intake/{lead_id}/documents", status_code=201)
async def upload_document(lead_id: UUID, file: UploadFile = File(...)):
    if not get_lead(lead_id):
        raise HTTPException(status_code=404, detail="Lead not found")
    settings = get_settings()
    filename = safe_filename(file.filename or "upload")
    extension = Path(filename).suffix.lower()
    if extension not in settings.upload_extensions:
        raise HTTPException(status_code=415, detail="File extension is not allowed")

    lead_dir = settings.upload_dir / str(lead_id)
    lead_dir.mkdir(parents=True, exist_ok=True)
    temporary_path = lead_dir / f".{filename}.part"
    final_path = lead_dir / filename
    max_bytes = settings.max_upload_mb * 1024 * 1024
    digest = hashlib.sha256()
    size = 0
    try:
        with temporary_path.open("wb") as target:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > max_bytes:
                    raise HTTPException(status_code=413, detail="File exceeds configured size limit")
                digest.update(chunk)
                target.write(chunk)
        temporary_path.replace(final_path)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise

    row = save_document(
        lead_id=lead_id,
        filename=filename,
        storage_path=str(final_path),
        media_type=file.content_type or "application/octet-stream",
        size_bytes=size,
        sha256=digest.hexdigest(),
    )
    if not row.get("inserted") and str(final_path) != row["storage_path"]:
        final_path.unlink(missing_ok=True)
    return {
        "document_id": row["id"],
        "sha256": row["sha256"],
        "status": row["validation_status"],
        "duplicate": not row.get("inserted", False),
    }


@app.get("/api/v1/internal/leads/{lead_id}", dependencies=[Depends(require_internal_key)])
def internal_get_lead(lead_id: UUID):
    lead = get_lead(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@app.post("/api/v1/internal/leads/{lead_id}/process", dependencies=[Depends(require_internal_key)])
def process_lead(lead_id: UUID, event_id: UUID | None = None):
    if event_id:
        processed = get_processed_event_lead(event_id)
        if processed:
            return {**processed, "already_processed": True}
    lead = get_lead(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    intake = IntakeCreate(
        source=lead["source"],
        contact_name=lead["contact_name"],
        company_name=lead["company_name"],
        email=lead["email"],
        phone=lead["phone"],
        country_code=lead["country_code"],
        industry=lead["industry"],
        employee_count=lead["employee_count"],
        monthly_document_volume=lead["monthly_document_volume"],
        annual_revenue_band=lead["annual_revenue_band"],
        requested_services=lead["requested_services"],
        urgency=lead["urgency"],
        message=lead["message"],
        consent_privacy=lead["consent_privacy"],
        consent_marketing=lead["consent_marketing"],
        website="",
    )
    provider = get_ai_provider()
    extraction, model_name = provider.extract(intake)
    result = score_lead(
        ScoringInput(
            employee_count=intake.employee_count,
            monthly_document_volume=intake.monthly_document_volume,
            annual_revenue_band=intake.annual_revenue_band,
            requested_services=list(intake.requested_services),
            urgency=intake.urgency,
            industry=intake.industry,
            has_documents=get_document_count(lead_id) > 0,
        ),
        extraction,
    )
    return save_processing_result(lead_id, extraction, model_name, result, PROMPT_VERSION, event_id)


@app.post("/api/v1/internal/leads/{lead_id}/status", dependencies=[Depends(require_internal_key)])
def internal_update_status(
    lead_id: UUID,
    update: StatusUpdate,
    x_actor_id: str = Header(default="n8n", alias="X-Actor-Id"),
):
    try:
        return update_lead_status(lead_id, update, x_actor_id[:160])
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/v1/internal/leads/{lead_id}/email", dependencies=[Depends(require_internal_key)])
def internal_send_email(lead_id: UUID, request: EmailRequest):
    lead = get_lead(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return send_template(request.template, lead)


@app.post("/api/v1/internal/workflow-errors", status_code=202, dependencies=[Depends(require_internal_key)])
def workflow_error(error: WorkflowError):
    record_workflow_error(error)
    logger.error("Workflow failure recorded: %s", error.workflow_name)
    return {"accepted": True}


@app.get("/api/v1/dashboard/leads", dependencies=[Depends(require_dashboard_key)])
def dashboard_leads(limit: int = 200):
    return list_dashboard_leads(min(max(limit, 1), 1000))


@app.get("/api/v1/dashboard/kpis", dependencies=[Depends(require_dashboard_key)])
def dashboard_metrics():
    return dashboard_kpis()


@app.post("/api/v1/dashboard/leads/{lead_id}/status", dependencies=[Depends(require_dashboard_key)])
def dashboard_update_status(
    lead_id: UUID,
    update: StatusUpdate,
    x_actor_id: str = Header(default="demo-reviewer", alias="X-Actor-Id"),
):
    try:
        return update_lead_status(lead_id, update, x_actor_id[:160])
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
