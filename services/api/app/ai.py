import json
import re
from abc import ABC, abstractmethod
from typing import Any

from app.config import get_settings
from app.schemas import AILeadExtraction, IntakeCreate

PROMPT_VERSION = "lead-extraction-v1"


class AIProvider(ABC):
    @abstractmethod
    def extract(self, intake: IntakeCreate) -> tuple[AILeadExtraction, str]:
        """Return validated extraction and the model/provider identifier."""


class MockAIProvider(AIProvider):
    """Deterministic, zero-cost provider for demos and tests."""

    def extract(self, intake: IntakeCreate) -> tuple[AILeadExtraction, str]:
        text = f"{intake.industry or ''} {intake.message}".lower()
        services = list(intake.requested_services)
        if "payroll" in text or "salar" in text:
            services.append("payroll")
        if "cash flow" in text or "cash-flow" in text:
            services.append("cash_flow_reporting")
        if "tax" in text or "fiscal" in text:
            services.append("tax_advisory")
        services = list(dict.fromkeys(services))

        industry = intake.industry
        if not industry:
            if any(token in text for token in ("shop", "ecommerce", "online store")):
                industry = "ecommerce"
            elif any(token in text for token in ("consult", "advisory")):
                industry = "consulting"

        missing: list[str] = []
        if intake.employee_count is None:
            missing.append("employee_count")
        if intake.monthly_document_volume is None:
            missing.append("monthly_document_volume")
        if intake.annual_revenue_band == "unknown":
            missing.append("annual_revenue_band")

        risk_flags: list[str] = []
        if re.search(r"\b(fraud|sanction|lawsuit|money laundering|evaziune)\b", text):
            risk_flags.append("sensitive_compliance_language")
        if intake.urgency == "critical":
            risk_flags.append("critical_urgency_requires_human_review")

        volume = intake.monthly_document_volume or 0
        complexity = "high" if volume >= 500 or len(services) >= 3 else "medium" if volume >= 100 else "low"
        next_action = "request_missing_information" if missing else (
            "schedule_discovery_call" if complexity in {"medium", "high"} else "manual_review"
        )

        extraction = AILeadExtraction(
            industry=industry,
            requested_services=services,
            urgency=intake.urgency,
            complexity=complexity,
            summary=(
                f"{intake.company_name} requests {', '.join(services)}. "
                f"The request is assessed as {complexity} complexity with {intake.urgency} urgency."
            ),
            missing_information=missing,
            next_action=next_action,
            confidence=0.92 if intake.industry and intake.monthly_document_volume is not None else 0.78,
            risk_flags=risk_flags,
        )
        return extraction, "mock-rules-v1"


def _strict_json_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Recursively constrain Pydantic JSON Schema for strict structured output."""
    if isinstance(schema, dict):
        result = {
            key: _strict_json_schema(value)
            for key, value in schema.items()
            if key not in {"default"}
        }
        if result.get("type") == "object":
            result["additionalProperties"] = False
            properties = result.get("properties", {})
            result["required"] = list(properties.keys())
        return result
    if isinstance(schema, list):
        return [_strict_json_schema(item) for item in schema]
    return schema


class OpenAIProvider(AIProvider):
    def __init__(self) -> None:
        settings = get_settings()
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required when AI_PROVIDER=openai")
        from openai import OpenAI

        self.settings = settings
        self.client = OpenAI(api_key=settings.openai_api_key, timeout=settings.ai_timeout_seconds)

    def extract(self, intake: IntakeCreate) -> tuple[AILeadExtraction, str]:
        schema = _strict_json_schema(AILeadExtraction.model_json_schema())
        system_prompt = (
            "You extract structured lead-intake facts for a fictional accounting firm. "
            "Use only information present in the request. Never invent financial facts. "
            "Mark missing information explicitly. AI output is advisory and must not approve, "
            "reject, price, or make legal/tax decisions. Return data matching the JSON schema."
        )
        user_payload = intake.model_dump(exclude={"website"}, mode="json")
        response = self.client.responses.create(
            model=self.settings.openai_model,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "fincore_lead_extraction",
                    "description": "Structured extraction from an accounting-firm lead intake.",
                    "schema": schema,
                    "strict": True,
                }
            },
            max_output_tokens=1200,
        )
        return AILeadExtraction.model_validate_json(response.output_text), self.settings.openai_model


def get_ai_provider() -> AIProvider:
    provider = get_settings().ai_provider.lower().strip()
    if provider == "openai":
        return OpenAIProvider()
    if provider == "mock":
        return MockAIProvider()
    raise ValueError(f"Unsupported AI_PROVIDER: {provider}")
