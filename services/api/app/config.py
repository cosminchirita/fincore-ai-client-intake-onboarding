from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    app_env: str = "development"
    log_level: str = "INFO"
    public_base_url: str = "http://localhost:8000"
    database_url: str = "postgresql://fincore:fincore_dev_only@localhost:5432/fincore"
    internal_api_key: str = Field(default="local-internal-key-change-me-1234567890", min_length=24)
    dashboard_api_key: str = Field(default="local-dashboard-key-change-me-123456789", min_length=24)

    ai_provider: str = "mock"
    openai_api_key: str | None = None
    openai_model: str = "gpt-5-mini"
    ai_timeout_seconds: float = 30.0
    ai_max_retries: int = 2

    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from: str = "FinCore Accounting <onboarding@fincore.demo>"
    internal_notification_email: str = "team@fincore.demo"

    upload_dir: Path = Path("/tmp/fincore-uploads")
    max_upload_mb: int = 10
    allowed_upload_extensions: str = ".pdf,.xlsx,.xls,.csv,.docx"
    retention_days: int = 90

    n8n_webhook_url: str = "http://localhost:5678/webhook/fincore-lead-intake"
    outbox_poll_seconds: int = 3
    outbox_max_attempts: int = 8

    @property
    def upload_extensions(self) -> set[str]:
        return {item.strip().lower() for item in self.allowed_upload_extensions.split(",") if item.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()
