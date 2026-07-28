import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.ai import MockAIProvider
from app.schemas import AILeadExtraction, IntakeCreate


def sample_intake() -> IntakeCreate:
    return IntakeCreate(
        contact_name="Elena Popescu",
        company_name="Northstar Commerce SRL",
        email="elena@example.com",
        industry="ecommerce",
        employee_count=18,
        monthly_document_volume=1200,
        annual_revenue_band="1m_5m",
        requested_services=["accounting"],
        urgency="high",
        message="We run an online shop and need accounting, payroll and cash flow reporting every month.",
        consent_privacy=True,
        website="",
    )


def test_mock_provider_returns_validated_schema():
    extraction, provider = MockAIProvider().extract(sample_intake())
    assert isinstance(extraction, AILeadExtraction)
    assert provider == "mock-rules-v1"
    assert "payroll" in extraction.requested_services


def test_schema_rejects_unknown_fields():
    payload = MockAIProvider().extract(sample_intake())[0].model_dump()
    payload["untrusted_decision"] = "approve"
    with pytest.raises(ValidationError):
        AILeadExtraction.model_validate(payload)


def test_published_json_schema_is_valid_json():
    path = Path(__file__).parents[1] / "schemas" / "ai_lead_extraction.schema.json"
    schema = json.loads(path.read_text())
    assert schema["additionalProperties"] is False
    assert "confidence" in schema["required"]
