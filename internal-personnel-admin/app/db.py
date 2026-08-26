from __future__ import annotations

import sqlite3
from collections.abc import Iterator

from .config import APP_ROOT, database_path, document_storage_path

SCHEMA_PATH = APP_ROOT / "app" / "schema.sql"


def connect() -> sqlite3.Connection:
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db() -> None:
    with connect() as connection:
        connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        document_storage_path().mkdir(parents=True, exist_ok=True)
        columns = {row[1] for row in connection.execute("PRAGMA table_info(people)")}
        if "line_id" not in columns:
            connection.execute("ALTER TABLE people ADD COLUMN line_id TEXT")
        if "birth_date" not in columns:
            connection.execute("ALTER TABLE people ADD COLUMN birth_date TEXT")
        document_columns = {row[1] for row in connection.execute("PRAGMA table_info(person_documents)")}
        if "storage_path" not in document_columns:
            connection.execute("ALTER TABLE person_documents ADD COLUMN storage_path TEXT")
        people_columns = {row[1] for row in connection.execute("PRAGMA table_info(people)")}
        if "bank_branch_code" not in people_columns:
            connection.execute("ALTER TABLE people ADD COLUMN bank_branch_code TEXT")
        if "professional_experience" not in people_columns:
            connection.execute("ALTER TABLE people ADD COLUMN professional_experience TEXT")
        if "permanent_address" not in people_columns:
            connection.execute("ALTER TABLE people ADD COLUMN permanent_address TEXT")
        labor_report_columns = {row[1] for row in connection.execute("PRAGMA table_info(labor_reports)")}
        if "work_start_date" not in labor_report_columns:
            connection.execute("ALTER TABLE labor_reports ADD COLUMN work_start_date TEXT")
        if "work_end_date" not in labor_report_columns:
            connection.execute("ALTER TABLE labor_reports ADD COLUMN work_end_date TEXT")
        if "voided_at" not in labor_report_columns:
            connection.execute("ALTER TABLE labor_reports ADD COLUMN voided_at TEXT")
        if "voided_by" not in labor_report_columns:
            connection.execute("ALTER TABLE labor_reports ADD COLUMN voided_by TEXT")


def get_db() -> Iterator[sqlite3.Connection]:
    connection = connect()
    try:
        yield connection
    finally:
        connection.close()
