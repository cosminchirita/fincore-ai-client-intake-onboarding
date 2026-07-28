from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

ServiceType = Literal[
    "accounting",
    "payroll",
    "tax_advisory",
    "cash_flow_reporting",
    "management_reporting",
    "document_digitization",
    "other",
]


class IntakeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    source: Literal["web_form", "email", "referral", "linkedin", "manual", "api"] = "web_form"
    contact_name: str = Field(min_length=2, max_length=160)
    company_name: str = Field(min_length=2, max_length=200)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=40)
    country_code: str | None = Field(default="RO", min_length=2, max_length=2)
    industry: str | None = Field(default=None, max_length=120)
    employee_count: int | None = Field(default=None, ge=1, le=1_000_000)
    monthly_document_volume: int | None = Field(default=None, ge=0, le=100_000_000)
    annual_revenue_band: Literal[
        "unknown", "under_100k", "100k_500k", "500k_1m", "1m_5m", "over_5m"
    ] = "unknown"
    requested_services: list[ServiceType] = Field(min_length=1, max_length=7)
    urgency: Literal["low", "normal", "high", "critical"] = "normal"
    message: str = Field(min_length=20, max_length=5000)
    consent_privacy: bool
    consent_marketing: bool = False
    website: str | None = Field(default=None, max_length=0, description="Honeypot; must remain empty")

    @field_validator("country_code")
    @classmethod
    def uppercase_country(cls, value: str | None) -> str | None:
        return value.upper() if value else value

    @field_validator("consent_privacy")
    @classmethod
    def require_privacy_consent(cls, value: bool) -> bool:
        if not value:
            raise ValueError("Privacy consent is required")
        return value


class AILeadExtraction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    industry: str | None = Field(default=None, max_length=120)
    requested_services: list[ServiceType]
    urgency: Literal["low", "normal", "high", "critical"]
    complexity: Literal["low", "medium", "high"]
    summary: str = Field(min_length=10, max_length=800)
    missing_information: list[str] = Field(max_length=12)
    next_action: Literal[
        "schedule_discovery_call",
        "request_missing_information",
        "manual_review",
    ]
    confidence: float = Field(ge=0, le=1)
    risk_flags: list[str] = Field(default_factory=list, max_length=12)


class ScoreBreakdown(BaseModel):
    data_completeness: int
    service_fit: int
    volume_fit: int
    urgency: int
    industry_fit: int
    document_readiness: int
    commercial_fit: int
    risk_penalty: int


class LeadScoreResult(BaseModel):
    score: int = Field(ge=0, le=100)
    priority: Literal["low", "medium", "high"]
    recommended_status: Literal["qualified", "review_required", "awaiting_information"]
    rules_version: str
    breakdown: ScoreBreakdown
    risk_flags: list[str]
    explanation: list[str]


class IntakeAccepted(BaseModel):
    lead_id: UUID
    correlation_id: UUID
    status: str
    message: str


class LeadRecord(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: UUID
    correlation_id: UUID
    status: str
    priority: str
    contact_name: str
    company_name: str
    email: EmailStr
    requested_services: list[str]
    urgency: str
    message: str
    created_at: datetime
    updated_at: datetime


class StatusUpdate(BaseModel):
    status: Literal[
        "received", "processing", "awaiting_information", "qualified",
        "review_required", "rejected", "onboarding", "active", "archived", "failed"
    ]
    assigned_to: str | None = Field(default=None, max_length=160)
    reason: str = Field(min_length=3, max_length=500)


class EmailRequest(BaseModel):
    template: Literal["qualified", "missing_information", "internal_notification", "onboarding"]


class WorkflowError(BaseModel):
    lead_id: UUID | None = None
    workflow_name: str = Field(max_length=160)
    execution_id: str | None = Field(default=None, max_length=255)
    current_step: str | None = Field(default=None, max_length=160)
    error_code: str | None = Field(default=None, max_length=80)
    error_message: str = Field(max_length=2000)
    attempt: int = Field(default=1, ge=1)
