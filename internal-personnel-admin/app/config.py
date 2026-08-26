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
    value = Path(os.environ.get("PERSONNEL_DATABASE_PATH", os.environ.get("DATABASE_PATH", "./data/personnel.db")))
    return value if value.is_absolute() else APP_ROOT / value


def document_storage_path() -> Path:
    value = Path(os.environ.get("DOCUMENT_STORAGE_PATH", "./data/personnel-documents"))
    return value if value.is_absolute() else APP_ROOT / value


def allowed_emails() -> set[str]:
    return {
        email.strip().lower()
        for email in os.environ.get("APP_ALLOWED_EMAILS", os.environ.get("ADMIN_ALLOWED_EMAILS", "")).split(",")
        if email.strip()
    }


def auth_mode() -> str:
    return os.environ.get("APP_AUTH_MODE", os.environ.get("ADMIN_AUTH_MODE", "dev")).strip().lower()


def dev_email() -> str:
    return os.environ.get("APP_DEV_EMAIL", os.environ.get("ADMIN_DEV_EMAIL", "local-admin@opusformosa.org")).strip().lower()


def base_url() -> str:
    return os.environ.get("BASE_URL", "").strip().rstrip("/")


def google_client_id() -> str:
    return os.environ.get("GOOGLE_CLIENT_ID", "").strip()


def google_client_secret() -> str:
    return os.environ.get("GOOGLE_CLIENT_SECRET", "").strip()


def smtp_host() -> str:
    return os.environ.get("SMTP_HOST", "mail.smtp2go.com").strip()


def smtp_port() -> int:
    try:
        return int(os.environ.get("SMTP_PORT", "587"))
    except ValueError:
        return 587


def smtp_username() -> str:
    return os.environ.get("SMTP_USERNAME", "").strip()


def smtp_password() -> str:
    return os.environ.get("SMTP_PASSWORD", "")


def mail_from() -> str:
    return os.environ.get("SMTP_FROM_EMAIL", os.environ.get("MAIL_FROM", "info@opusformosa.org")).strip()


def mail_from_name() -> str:
    return os.environ.get("SMTP_FROM_NAME", "Opus Formosa").strip()


def smtp_enabled() -> bool:
    return bool(smtp_host() and smtp_username() and smtp_password() and mail_from())
