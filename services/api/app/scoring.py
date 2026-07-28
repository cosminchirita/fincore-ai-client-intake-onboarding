from dataclasses import dataclass
from typing import Any

from app.schemas import AILeadExtraction, LeadScoreResult, ScoreBreakdown

RULES_VERSION = "2026-01"
SUPPORTED_SERVICES = {
    "accounting",
    "payroll",
    "tax_advisory",
    "cash_flow_reporting",
    "management_reporting",
    "document_digitization",
}
PREFERRED_INDUSTRIES = {
    "ecommerce",
    "professional_services",
    "consulting",
    "saas",
    "retail",
    "manufacturing",
    "healthcare",
}


@dataclass(frozen=True)
class ScoringInput:
    employee_count: int | None
    monthly_document_volume: int | None
    annual_revenue_band: str | None
    requested_services: list[str]
    urgency: str
    industry: str | None
    has_documents: bool = False


def score_lead(data: ScoringInput, extraction: AILeadExtraction) -> LeadScoreResult:
    explanation: list[str] = []

    known_fields = sum(
        value not in (None, "", "unknown", [])
        for value in (
            data.employee_count,
            data.monthly_document_volume,
            data.annual_revenue_band,
            data.industry,
            data.requested_services,
        )
    )
    completeness = min(15, known_fields * 3)
    explanation.append(f"Data completeness contributes {completeness}/15 points.")

    matched_services = set(data.requested_services) & SUPPORTED_SERVICES
    service_fit = min(20, 10 + 5 * len(matched_services)) if matched_services else 0
    explanation.append(f"Supported service fit contributes {service_fit}/20 points.")

    volume = data.monthly_document_volume or 0
    if volume >= 500:
        volume_fit = 15
    elif volume >= 100:
        volume_fit = 10
    elif volume > 0:
        volume_fit = 5
    else:
        volume_fit = 0
    explanation.append(f"Monthly document volume contributes {volume_fit}/15 points.")

    urgency_points = {"low": 2, "normal": 5, "high": 8, "critical": 10}[data.urgency]
    explanation.append(f"Urgency contributes {urgency_points}/10 points.")

    normalized_industry = (data.industry or extraction.industry or "").strip().lower()
    industry_fit = 10 if normalized_industry in PREFERRED_INDUSTRIES else (5 if normalized_industry else 0)
    explanation.append(f"Industry fit contributes {industry_fit}/10 points.")

    document_readiness = 10 if data.has_documents else 2
    explanation.append(f"Document readiness contributes {document_readiness}/10 points.")

    revenue_points = {
        "under_100k": 5,
        "100k_500k": 10,
        "500k_1m": 14,
        "1m_5m": 18,
        "over_5m": 20,
        "unknown": 5,
        None: 5,
    }.get(data.annual_revenue_band, 5)
    commercial_fit = revenue_points
    explanation.append(f"Commercial fit contributes {commercial_fit}/20 points.")

    risk_flags = list(dict.fromkeys(extraction.risk_flags))
    risk_penalty = -5 * min(len(risk_flags), 3)
    if extraction.confidence < 0.65:
        risk_flags.append("low_ai_confidence")
        risk_penalty -= 5
    risk_penalty = max(-20, risk_penalty)
    explanation.append(f"Risk controls contribute {risk_penalty} points.")

    raw_score = (
        completeness + service_fit + volume_fit + urgency_points + industry_fit
        + document_readiness + commercial_fit + risk_penalty
    )
    score = max(0, min(100, raw_score))

    if extraction.missing_information:
        recommended_status = "awaiting_information"
    elif score >= 80:
        recommended_status = "qualified"
        if "human_review_before_contract" not in risk_flags:
            risk_flags.append("human_review_before_contract")
    else:
        recommended_status = "review_required"

    priority = "high" if score >= 80 else "medium" if score >= 50 else "low"

    return LeadScoreResult(
        score=score,
        priority=priority,
        recommended_status=recommended_status,
        rules_version=RULES_VERSION,
        breakdown=ScoreBreakdown(
            data_completeness=completeness,
            service_fit=service_fit,
            volume_fit=volume_fit,
            urgency=urgency_points,
            industry_fit=industry_fit,
            document_readiness=document_readiness,
            commercial_fit=commercial_fit,
            risk_penalty=risk_penalty,
        ),
        risk_flags=list(dict.fromkeys(risk_flags)),
        explanation=explanation,
    )


def score_payload(result: LeadScoreResult) -> dict[str, Any]:
    return result.model_dump(mode="json")
