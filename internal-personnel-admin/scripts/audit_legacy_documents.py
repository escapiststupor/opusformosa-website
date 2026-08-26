#!/usr/bin/env python3
"""Print private document paths that do not yet have a download record."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("database", type=Path)
    parser.add_argument("document_root", type=Path)
    args = parser.parse_args()
    with sqlite3.connect(args.database) as connection:
        indexed = {row[0] for row in connection.execute("SELECT storage_path FROM person_documents WHERE storage_path IS NOT NULL")}
    files = {
        str(path.relative_to(args.document_root))
        for path in args.document_root.rglob("*")
        if path.is_file() and path.name not in {"source.tar.gz", ".DS_Store"} and not path.name.startswith("._")
    }
    unindexed = sorted(files - indexed)
    print(f"indexed={len(indexed)} files={len(files)} unindexed={len(unindexed)}")
    print("\n".join(unindexed))


if __name__ == "__main__":
    main()
