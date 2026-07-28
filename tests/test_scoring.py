from app.schemas import AILeadExtraction
from app.scoring import ScoringInput, score_lead


def extraction(**overrides):
    data = {
        "industry": "ecommerce",
        "requested_services": ["accounting", "payroll", "cash_flow_reporting"],
        "urgency": "high",
        "complexity": "high",
        "summary": "Ecommerce company requesting an integrated finance service.",
        "missing_information": [],
        "next_action": "schedule_discovery_call",
        "confidence": 0.94,
        "risk_flags": [],
    }
    data.update(overrides)
    return AILeadExtraction(**data)


def test_high_fit_lead_is_qualified_but_requires_human_review():
    result = score_lead(
        ScoringInput(
            employee_count=18,
            monthly_document_volume=1200,
            annual_revenue_band="1m_5m",
            requested_services=["accounting", "payroll", "cash_flow_reporting"],
            urgency="high",
            industry="ecommerce",
            has_documents=True,
        ),
        extraction(),
    )
    assert result.score >= 80
    assert result.priority == "high"
    assert result.recommended_status == "qualified"
    assert "human_review_before_contract" in result.risk_flags


def test_missing_information_prevents_auto_qualification():
    result = score_lead(
        ScoringInput(
            employee_count=None,
            monthly_document_volume=None,
            annual_revenue_band="unknown",
            requested_services=["accounting"],
            urgency="normal",
            industry=None,
            has_documents=False,
        ),
        extraction(
            industry=None,
            requested_services=["accounting"],
            complexity="low",
            missing_information=["employee_count", "monthly_document_volume"],
            next_action="request_missing_information",
            confidence=0.72,
        ),
    )
    assert result.recommended_status == "awaiting_information"
    assert 0 <= result.score <= 100


def test_risk_flags_reduce_score():
    base = ScoringInput(
        employee_count=12,
        monthly_document_volume=500,
        annual_revenue_band="500k_1m",
        requested_services=["accounting", "payroll"],
        urgency="high",
        industry="ecommerce",
        has_documents=True,
    )
    clean = score_lead(base, extraction())
    risky = score_lead(base, extraction(risk_flags=["sensitive_compliance_language"]))
    assert risky.score < clean.score
