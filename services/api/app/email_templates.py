from app.config import get_settings


def render_email(template: str, lead: dict) -> tuple[str, str, str]:
    first_name = str(lead["contact_name"]).split()[0]
    missing = ", ".join(lead.get("missing_information") or [])
    templates = {
        "qualified": (
            "Thank you — next step with FinCore Accounting",
            f"Hello {first_name},\n\nThank you for your request. Based on the information provided, "
            "the next appropriate step is a discovery call with a FinCore specialist. "
            "A human reviewer will confirm scope, availability and commercial terms before any engagement.\n\n"
            "Regards,\nFinCore Accounting (demo)",
            str(lead["email"]),
        ),
        "missing_information": (
            "Additional information needed for your FinCore request",
            f"Hello {first_name},\n\nThank you for contacting FinCore Accounting. "
            f"To review your request, we still need: {missing or 'a few operational details'}.\n\n"
            "Please reply without sending sensitive personal or financial records by email. "
            "Use the secure upload link provided by the team when available.\n\nRegards,\nFinCore Accounting (demo)",
            str(lead["email"]),
        ),
        "onboarding": (
            "FinCore onboarding checklist",
            f"Hello {first_name},\n\nYour request has been approved for onboarding by a human reviewer. "
            "Please prepare company registration details, current accounting software information, "
            "monthly transaction estimates and the agreed document checklist.\n\nRegards,\nFinCore Accounting (demo)",
            str(lead["email"]),
        ),
        "internal_notification": (
            f"FinCore lead review: {lead['company_name']}",
            f"A lead requires review.\n\nCompany: {lead['company_name']}\n"
            f"Priority: {lead['priority']}\nStatus: {lead['status']}\n"
            f"Summary: {lead.get('ai_summary') or 'Not processed'}\nLead ID: {lead['id']}",
            get_settings().internal_notification_email,
        ),
    }
    if template not in templates:
        raise ValueError(f"Unknown email template: {template}")
    return templates[template]
