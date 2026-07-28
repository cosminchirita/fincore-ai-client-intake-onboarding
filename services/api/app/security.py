import hashlib
import hmac
from pathlib import Path

from fastapi import Header, HTTPException, status

from app.config import get_settings


def require_internal_key(x_internal_api_key: str = Header(default="")) -> None:
    expected = get_settings().internal_api_key.encode()
    supplied = x_internal_api_key.encode()
    if not hmac.compare_digest(expected, supplied):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid internal API key")


def require_dashboard_key(x_dashboard_api_key: str = Header(default="")) -> None:
    expected = get_settings().dashboard_api_key.encode()
    supplied = x_dashboard_api_key.encode()
    if not hmac.compare_digest(expected, supplied):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid dashboard API key")


def pseudonymize(value: str | None) -> str | None:
    if not value:
        return None
    key = get_settings().internal_api_key.encode()
    return hmac.new(key, value.encode(), hashlib.sha256).hexdigest()


def safe_filename(filename: str) -> str:
    name = Path(filename).name.replace("\x00", "")
    return "".join(ch for ch in name if ch.isalnum() or ch in {".", "-", "_"})[:180]
