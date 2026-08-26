#!/usr/bin/env python3
"""Update the email of one existing person by name."""

from __future__ import annotations

import argparse
import sqlite3


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("database")
    parser.add_argument("name")
    parser.add_argument("email")
    args = parser.parse_args()
    with sqlite3.connect(args.database) as connection:
        result = connection.execute(
            "UPDATE people SET email = ?, updated_at = CURRENT_TIMESTAMP WHERE display_name = ? OR legal_name_zh = ?",
            (args.email, args.name, args.name),
        )
        if result.rowcount != 1:
            raise RuntimeError(f"Expected one person named {args.name}, found {result.rowcount}")
        print(f"updated={args.name}")


if __name__ == "__main__":
    main()
