import json
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from app.config import get_settings
from app.db import get_pool
from app.schemas import AILeadExtraction, IntakeCreate, LeadScoreResult, StatusUpdate, WorkflowError


def create_lead(intake: IntakeCreate, audit: dict[str, Any]) -> dict[str, Any]:
    settings = get_settings()
    event_id = uuid4()
    with get_pool().connection() as conn, conn.transaction():
        lead = conn.execute(
            """
            INSERT INTO leads (
              source, contact_name, company_name, email, phone, country_code, industry,
              employee_count, monthly_document_volume, annual_revenue_band,
              requested_services, urgency, message, consent_privacy, consent_marketing,
              retention_until
            ) VALUES (
              %(source)s, %(contact_name)s, %(company_name)s, %(email)s, %(phone)s,
              %(country_code)s, %(industry)s, %(employee_count)s, %(monthly_document_volume)s,
              %(annual_revenue_band)s, %(requested_services)s, %(urgency)s, %(message)s,
              %(consent_privacy)s, %(consent_marketing)s, current_date + %(retention_days)s
            )
            RETURNING *
            """,
            {
                **intake.model_dump(exclude={"website"}, mode="python"),
                "email": str(intake.email),
                "retention_days": settings.retention_days,
            },
        ).fetchone()
        conn.execute(
            """
            INSERT INTO outbox_events (id, aggregate_type, aggregate_id, event_type, payload)
            VALUES (%(event_id)s, 'lead', %(lead_id)s, 'lead.received', %(payload)s::jsonb)
            """,
            {
                "event_id": event_id,
                "lead_id": lead["id"],
                "payload": json.dumps(
                    {
                        "event_id": str(event_id),
                        "lead_id": str(lead["id"]),
                        "correlation_id": str(lead["correlation_id"]),
                    }
                ),
            },
        )
        conn.execute(
            """
            INSERT INTO audit_events (
              correlation_id, actor_type, actor_id, action, resource_type, resource_id,
              outcome, ip_hash, user_agent_hash, metadata
            ) VALUES (
              %(correlation_id)s, 'anonymous', NULL, 'lead.created', 'lead', %(resource_id)s,
              'success', %(ip_hash)s, %(user_agent_hash)s, %(metadata)s::jsonb
            )
            """,
            {
                "correlation_id": lead["correlation_id"],
                "resource_id": str(lead["id"]),
                "ip_hash": audit.get("ip_hash"),
                "user_agent_hash": audit.get("user_agent_hash"),
                "metadata": json.dumps({"source": intake.source, "privacy_consent": True}),
            },
        )
        return dict(lead)


def get_lead(lead_id: UUID) -> dict[str, Any] | None:
    with get_pool().connection() as conn:
        row = conn.execute("SELECT * FROM leads WHERE id = %s", (lead_id,)).fetchone()
        return dict(row) if row else None


def get_document_count(lead_id: UUID) -> int:
    with get_pool().connection() as conn:
        row = conn.execute("SELECT count(*) AS total FROM documents WHERE lead_id = %s", (lead_id,)).fetchone()
        return int(row["total"])


def save_processing_result(
    lead_id: UUID,
    extraction: AILeadExtraction,
    model_name: str,
    score: LeadScoreResult,
    prompt_version: str,
    event_id: UUID | None = None,
) -> dict[str, Any]:
    with get_pool().connection() as conn, conn.transaction():
        lead = conn.execute(
            """
            UPDATE leads SET
              status = %(status)s,
              priority = %(priority)s,
              industry = COALESCE(industry, %(industry)s),
              requested_services = %(services)s,
              urgency = %(urgency)s,
              ai_summary = %(summary)s,
              ai_complexity = %(complexity)s,
              ai_confidence = %(confidence)s,
              missing_information = %(missing)s,
              next_action = %(next_action)s,
              ai_model = %(model_name)s,
              ai_prompt_version = %(prompt_version)s,
              ai_processed_at = timezone('utc', now())
            WHERE id = %(lead_id)s
            RETURNING *
            """,
            {
                "lead_id": lead_id,
                "status": score.recommended_status,
                "priority": score.priority,
                "industry": extraction.industry,
                "services": extraction.requested_services,
                "urgency": extraction.urgency,
                "summary": extraction.summary,
                "complexity": extraction.complexity,
                "confidence": extraction.confidence,
                "missing": extraction.missing_information,
                "next_action": extraction.next_action,
                "model_name": model_name,
                "prompt_version": prompt_version,
            },
        ).fetchone()
        if not lead:
            raise KeyError(f"Lead {lead_id} not found")
        conn.execute(
            """
            INSERT INTO lead_scores (lead_id, score, rules_version, breakdown, risk_flags)
            VALUES (%s, %s, %s, %s::jsonb, %s)
            """,
            (
                lead_id,
                score.score,
                score.rules_version,
                json.dumps(score.breakdown.model_dump()),
                score.risk_flags,
            ),
        )
        conn.execute(
            """
            INSERT INTO audit_events (
              correlation_id, actor_type, actor_id, action, resource_type, resource_id,
              outcome, metadata
            ) VALUES (%s, 'service', 'intake-api', 'lead.ai_scored', 'lead', %s,
                      'success', %s::jsonb)
            """,
            (
                lead["correlation_id"],
                str(lead_id),
                json.dumps(
                    {
                        "score": score.score,
                        "rules_version": score.rules_version,
                        "ai_model": model_name,
                        "prompt_version": prompt_version,
                        "event_id": str(event_id) if event_id else None,
                        "decision_is_advisory": True,
                    }
                ),
            ),
        )
        if event_id:
            conn.execute(
                "INSERT INTO processed_events (event_id, lead_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                (event_id, lead_id),
            )
        return {**dict(lead), "score": score.model_dump(mode="json"), "already_processed": False}


def update_lead_status(lead_id: UUID, update: StatusUpdate, actor_id: str) -> dict[str, Any]:
    with get_pool().connection() as conn, conn.transaction():
        lead = conn.execute(
            """
            UPDATE leads SET status = %(status)s, assigned_to = COALESCE(%(assigned_to)s, assigned_to)
            WHERE id = %(lead_id)s RETURNING *
            """,
            {"lead_id": lead_id, "status": update.status, "assigned_to": update.assigned_to},
        ).fetchone()
        if not lead:
            raise KeyError(f"Lead {lead_id} not found")
        conn.execute(
            """
            INSERT INTO audit_events (
              correlation_id, actor_type, actor_id, action, resource_type, resource_id,
              outcome, metadata
            ) VALUES (%s, 'user', %s, 'lead.status_changed', 'lead', %s, 'success', %s::jsonb)
            """,
            (
                lead["correlation_id"],
                actor_id,
                str(lead_id),
                json.dumps({"status": update.status, "reason": update.reason}),
            ),
        )
        return dict(lead)


def save_document(
    lead_id: UUID,
    filename: str,
    storage_path: str,
    media_type: str,
    size_bytes: int,
    sha256: str,
) -> dict[str, Any]:
    with get_pool().connection() as conn, conn.transaction():
        row = conn.execute(
            """
            INSERT INTO documents (
              lead_id, original_filename, storage_path, media_type, size_bytes, sha256
            ) VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (lead_id, sha256) DO NOTHING
            RETURNING *, true AS inserted
            """,
            (lead_id, filename, storage_path, media_type, size_bytes, sha256),
        ).fetchone()
        if not row:
            row = conn.execute(
                "SELECT *, false AS inserted FROM documents WHERE lead_id = %s AND sha256 = %s",
                (lead_id, sha256),
            ).fetchone()
        conn.execute(
            """
            INSERT INTO audit_events (actor_type, actor_id, action, resource_type, resource_id, outcome, metadata)
            VALUES ('anonymous', NULL, 'document.uploaded', 'document', %s, 'success', %s::jsonb)
            """,
            (
                str(row["id"]),
                json.dumps({"lead_id": str(lead_id), "sha256": sha256, "size": size_bytes}),
            ),
        )
        return dict(row)


def record_interaction(
    lead_id: UUID,
    direction: str,
    interaction_type: str,
    subject: str,
    content_redacted: str,
    delivery_status: str,
    external_message_id: str | None = None,
) -> None:
    with get_pool().connection() as conn, conn.transaction():
        conn.execute(
            """
            INSERT INTO interactions (
              lead_id, channel, direction, interaction_type, subject, content_redacted,
              external_message_id, delivery_status
            ) VALUES (%s, 'email', %s, %s, %s, %s, %s, %s)
            """,
            (
                lead_id,
                direction,
                interaction_type,
                subject,
                content_redacted,
                external_message_id,
                delivery_status,
            ),
        )


def record_workflow_error(error: WorkflowError) -> None:
    redacted = error.error_message[:500].replace("\n", " ")
    with get_pool().connection() as conn, conn.transaction():
        conn.execute(
            """
            INSERT INTO workflow_runs (
              lead_id, workflow_name, external_execution_id, status, current_step,
              error_code, error_message_redacted, attempt, completed_at
            ) VALUES (%s, %s, %s, 'failed', %s, %s, %s, %s, timezone('utc', now()))
            """,
            (
                error.lead_id,
                error.workflow_name,
                error.execution_id,
                error.current_step,
                error.error_code,
                redacted,
                error.attempt,
            ),
        )
        if error.lead_id:
            conn.execute(
                "UPDATE leads SET status = 'failed' WHERE id = %s AND status IN ('received', 'processing')",
                (error.lead_id,),
            )


def list_dashboard_leads(limit: int = 200) -> list[dict[str, Any]]:
    with get_pool().connection() as conn:
        rows = conn.execute("SELECT * FROM dashboard_leads ORDER BY created_at DESC LIMIT %s", (limit,)).fetchall()
        return [dict(row) for row in rows]


def dashboard_kpis() -> dict[str, Any]:
    with get_pool().connection() as conn:
        row = conn.execute("SELECT * FROM dashboard_kpis").fetchone()
        return dict(row)


def claim_outbox_events(worker_id: str, limit: int = 20) -> list[dict[str, Any]]:
    with get_pool().connection() as conn, conn.transaction():
        rows = conn.execute(
            """
            WITH candidates AS (
              SELECT id FROM outbox_events
              WHERE (
                (status = 'pending' AND available_at <= timezone('utc', now()))
                OR (status = 'processing' AND locked_at < timezone('utc', now()) - interval '5 minutes')
              )
              ORDER BY created_at
              FOR UPDATE SKIP LOCKED
              LIMIT %s
            )
            UPDATE outbox_events o
            SET status = 'processing', locked_at = timezone('utc', now()), locked_by = %s,
                attempts = attempts + 1
            FROM candidates c
            WHERE o.id = c.id
            RETURNING o.*
            """,
            (limit, worker_id),
        ).fetchall()
        return [dict(row) for row in rows]


def complete_outbox_event(event_id: UUID) -> None:
    with get_pool().connection() as conn, conn.transaction():
        conn.execute(
            """
            UPDATE outbox_events SET status='delivered', delivered_at=timezone('utc', now()),
              locked_at=NULL, locked_by=NULL WHERE id=%s
            """,
            (event_id,),
        )


def retry_outbox_event(event: dict[str, Any], error: str) -> None:
    settings = get_settings()
    attempts = int(event["attempts"])
    status = "dead_letter" if attempts >= settings.outbox_max_attempts else "pending"
    delay_seconds = min(900, 2**attempts)
    with get_pool().connection() as conn, conn.transaction():
        conn.execute(
            """
            UPDATE outbox_events SET status=%s, available_at=%s, last_error_redacted=%s,
              locked_at=NULL, locked_by=NULL WHERE id=%s
            """,
            (
                status,
                datetime.now(UTC) + timedelta(seconds=delay_seconds),
                error[:500],
                event["id"],
            ),
        )


def get_idempotent_response(key: str, request_hash: str) -> tuple[int, dict[str, Any]] | None:
    with get_pool().connection() as conn:
        row = conn.execute(
            """
            SELECT response_code, response_body, request_hash FROM idempotency_keys
            WHERE key = %s AND expires_at > timezone('utc', now())
            """,
            (key,),
        ).fetchone()
        if not row:
            return None
        if row["request_hash"] != request_hash:
            raise ValueError("Idempotency key was already used with a different payload")
        return int(row["response_code"]), dict(row["response_body"])


def save_idempotent_response(key: str, request_hash: str, response_code: int, body: dict[str, Any]) -> None:
    with get_pool().connection() as conn, conn.transaction():
        conn.execute(
            """
            INSERT INTO idempotency_keys (key, request_hash, response_code, response_body, expires_at)
            VALUES (%s, %s, %s, %s::jsonb, timezone('utc', now()) + interval '24 hours')
            ON CONFLICT (key) DO NOTHING
            """,
            (key, request_hash, response_code, json.dumps(body)),
        )


def get_processed_event_lead(event_id: UUID) -> dict[str, Any] | None:
    with get_pool().connection() as conn:
        row = conn.execute(
            """
            SELECT l.* FROM processed_events p
            JOIN leads l ON l.id = p.lead_id
            WHERE p.event_id = %s
            """,
            (event_id,),
        ).fetchone()
        return dict(row) if row else None
