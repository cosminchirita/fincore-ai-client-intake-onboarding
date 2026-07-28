import json
import os
import uuid

import httpx

BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://localhost:8000")

payload = {
    "source": "api",
    "contact_name": "Elena Popescu",
    "company_name": "Northstar Commerce SRL",
    "email": "elena.popescu@example.com",
    "country_code": "RO",
    "industry": "ecommerce",
    "employee_count": 18,
    "monthly_document_volume": 1200,
    "annual_revenue_band": "1m_5m",
    "requested_services": ["accounting", "payroll", "cash_flow_reporting"],
    "urgency": "high",
    "message": "We operate an online shop and need accounting, payroll and monthly cash-flow reporting.",
    "consent_privacy": True,
    "consent_marketing": False,
    "website": "",
}

response = httpx.post(
    f"{BASE_URL}/api/v1/intake",
    json=payload,
    headers={"Idempotency-Key": str(uuid.uuid4())},
    timeout=15,
)
response.raise_for_status()
print(json.dumps(response.json(), indent=2))
