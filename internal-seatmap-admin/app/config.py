from __future__ import annotations

import os
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1]

try:
    from dotenv import load_dotenv

    load_dotenv(APP_ROOT / ".env")
except ImportError:
    pass


def database_path() -> Path:
    raw = os.environ.get("DATABASE_PATH", "./data/seatmap.db")
    path = Path(raw)
    if not path.is_absolute():
        path = APP_ROOT / path
    return path


def opentix_assets_dir() -> Path:
    raw = os.environ.get("OPENTIX_ASSETS_DIR", "").strip()
    if raw:
        path = Path(raw)
        if not path.is_absolute():
            path = APP_ROOT / path
        return path
    return database_path().parent / "opentix"


def allowed_admin_emails() -> set[str]:
    raw = os.environ.get("ADMIN_ALLOWED_EMAILS", "")
    return {email.strip().lower() for email in raw.split(",") if email.strip()}


def cors_origins() -> list[str]:
    raw = os.environ.get(
        "CORS_ORIGINS",
        "https://opusformosa.org,https://www.opusformosa.org,http://localhost:8000,http://127.0.0.1:8000",
    )
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def base_url() -> str:
    return os.environ.get("BASE_URL", "").strip().rstrip("/")


def google_client_id() -> str:
    return os.environ.get("GOOGLE_CLIENT_ID", "").strip()


def google_client_secret() -> str:
    return os.environ.get("GOOGLE_CLIENT_SECRET", "").strip()


def auth_mode() -> str:
    return os.environ.get("ADMIN_AUTH_MODE", "dev").strip().lower()


def dev_admin_email() -> str:
    return os.environ.get("ADMIN_DEV_EMAIL", "local-admin@opusformosa.org").strip().lower()


def seatmap_sync_token() -> str:
    return os.environ.get("SEATMAP_SYNC_TOKEN", "").strip()
