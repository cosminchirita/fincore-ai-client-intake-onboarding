from app.email_templates import render_email


def test_missing_information_email_does_not_echo_sensitive_message():
    lead = {
        "id": "11111111-1111-4111-8111-111111111111",
        "contact_name": "Elena Popescu",
        "company_name": "Demo SRL",
        "email": "elena@example.com",
        "priority": "medium",
        "status": "awaiting_information",
        "missing_information": ["monthly_document_volume"],
        "message": "SECRET SHOULD NOT BE ECHOED",
    }
    subject, body, recipient = render_email("missing_information", lead)
    assert "SECRET SHOULD NOT BE ECHOED" not in body
    assert "monthly_document_volume" in body
    assert recipient == "elena@example.com"
    assert subject
