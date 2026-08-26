#!/usr/bin/env python3
"""Import the specifically approved people from the salary/reporting tab."""

from __future__ import annotations

import argparse
import sqlite3
import uuid


PEOPLE = (
    ("曾柏雄", "行政", "E123775989"),
    ("柯曉慧", "行政", "A980030107"),
    ("劉虹麟", "音樂家", "L224226142"),
    ("郭保伸", "設計師", ""),
    ("徐華", "寫曲解的", ""),
)
SOURCE_NOTE = "資料來源：薪資與勞報明細（2026-08-25 匯入）"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("database")
    args = parser.parse_args()

    with sqlite3.connect(args.database) as connection:
        added = 0
        for name, role, identity_number in PEOPLE:
            existing = connection.execute(
                "SELECT id FROM people WHERE display_name = ? OR legal_name_zh = ?",
                (name, name),
            ).fetchone()
            if existing:
                person_id = existing[0]
            else:
                person_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"opusformosa-person:{name}"))
                connection.execute(
                    """INSERT INTO people (
                        id, display_name, legal_name_zh, id_document_type,
                        id_document_number, id_document_status, notes, is_active
                    ) VALUES (?, ?, ?, ?, ?, 'missing', ?, 1)""",
                    (person_id, name, name, "身分證" if identity_number else "", identity_number, SOURCE_NOTE),
                )
                added += 1
            connection.execute(
                "INSERT OR IGNORE INTO person_roles (person_id, role_name) VALUES (?, ?)",
                (person_id, role),
            )
        print(f"added={added} processed={len(PEOPLE)}")


if __name__ == "__main__":
    main()
