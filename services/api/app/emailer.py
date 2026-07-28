import smtplib
from email.message import EmailMessage
from uuid import UUID

from app.config import get_settings
from app.email_templates import render_email
from app.repository import record_interaction


def send_template(template: str, lead: dict) -> dict[str, str]:
    subject, body, recipient = render_email(template, lead)
    settings = get_settings()
    message = EmailMessage()
    message["From"] = settings.smtp_from
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)

    delivery_status = "failed"
    external_id: str | None = None
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
            if settings.smtp_username and settings.smtp_password:
                smtp.starttls()
                smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(message)
        delivery_status = "sent"
        external_id = message.get("Message-ID")
        return {"status": delivery_status, "recipient": recipient, "subject": subject}
    finally:
        record_interaction(
            lead_id=UUID(str(lead["id"])),
            direction="internal" if template == "internal_notification" else "outbound",
            interaction_type=template,
            subject=subject,
            content_redacted=f"Template={template}; recipient_domain={recipient.split('@')[-1]}",
            delivery_status=delivery_status,
            external_message_id=external_id,
        )
