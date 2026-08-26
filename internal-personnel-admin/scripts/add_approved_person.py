#!/usr/bin/env python3
"""Add one explicitly approved person to the internal directory."""

from __future__ import annotations

import argparse
import sqlite3
import uuid


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("database")
    parser.add_argument("name")
    parser.add_argument("role")
    args = parser.parse_args()
    with sqlite3.connect(args.database) as connection:
        row = connection.execute(
            "SELECT id FROM people WHERE display_name = ? OR legal_name_zh = ?",
            (args.name, args.name),
        ).fetchone()
        if row:
            person_id = row[0]
            created = False
        else:
            person_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"opusformosa-person:{args.name}"))
            connection.execute(
                "INSERT INTO people (id, display_name, legal_name_zh, id_document_status, is_active) VALUES (?, ?, ?, 'missing', 1)",
                (person_id, args.name, args.name),
            )
            connection.execute("INSERT INTO audit_log (person_id, action, actor_email) VALUES (?, 'created', 'legacy-import')", (person_id,))
            created = True
        connection.execute("INSERT OR IGNORE INTO person_roles (person_id, role_name) VALUES (?, ?)", (person_id, args.role))
        connection.commit()
    print(f"person_id={person_id} created={created}")


if __name__ == "__main__":
    main()
