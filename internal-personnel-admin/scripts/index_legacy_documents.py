#!/usr/bin/env python3
"""Create download records for existing, unambiguous private identity files."""

from __future__ import annotations

import argparse
import mimetypes
import sqlite3
import uuid
from pathlib import Path


ID_FOLDER_PEOPLE = {
    "丁章媛", "劉虹麟", "曾柏雄", "柯曉慧", "陳逸庭",
}
ID_FOLDER_ALIASES = {"江月萱(StevenMom)": "江月萱"}
ORCHESTRA_PEOPLE = {
    "侯傳安", "劉品均", "劉哲川", "張仲薇", "張頌奇", "徐溢恩", "曾婕安",
    "李騏", "蕭佳倩", "連珮致", "鄒佳宏", "陳志達", "黃哲筠",
}
FOREIGN_PASSPORTS = {
    "aimi-sorita": "Aimi Sorita",
    "adrien-la-marca": "Adrien La Marca",
    "boris-borgolotto": "Boris Borgolotto",
    "brannon-cho": "Brannon Cho",
    "edgar-moreau": "Edgar Moreau",
    "jinjoo-cho": "Jinjoo Cho",
    "kyu-yeon-kim": "Kyu Yeon Kim",
    "sirena-huang": "Sirena Huang",
}
EXTRA_PATH_PEOPLE = {
    "imports/ids-2026-08-25/IDs/林易F800208677.pdf": "林易",
    "imports/ids-2026-08-25/IDs/passport/borisborgolotto.jpg": "Boris Borgolotto",
    "imports/ids-2026-08-25/IDs/負責人身分證影本.jpg": "王資閔",
}


def person_name_for_path(relative: Path) -> str | None:
    if str(relative) in EXTRA_PATH_PEOPLE:
        return EXTRA_PATH_PEOPLE[str(relative)]
    parts = relative.parts
    if len(parts) >= 5 and parts[:3] == ("imports", "ids-2026-08-25", "IDs"):
        if parts[3] in ID_FOLDER_PEOPLE:
            return parts[3]
        if parts[3] in ID_FOLDER_ALIASES:
            return ID_FOLDER_ALIASES[parts[3]]
        if len(parts) >= 6 and parts[3] == "樂團團員" and parts[4] in ORCHESTRA_PEOPLE:
            return parts[4]
    if len(parts) == 3 and parts[0] == "foreign-passports" and parts[2] == "passport.pdf":
        return FOREIGN_PASSPORTS.get(parts[1])
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("database", type=Path)
    parser.add_argument("document_root", type=Path)
    args = parser.parse_args()
    with sqlite3.connect(args.database) as connection:
        connection.row_factory = sqlite3.Row
        inserted = 0
        skipped = 0
        for path in sorted(args.document_root.rglob("*")):
            if not path.is_file() or path.name in {"source.tar.gz", ".DS_Store"} or path.name.startswith("._"):
                continue
            relative = path.relative_to(args.document_root)
            person_name = person_name_for_path(relative)
            if not person_name:
                skipped += 1
                continue
            person = connection.execute(
                "SELECT id FROM people WHERE display_name = ? OR legal_name_zh = ? OR legal_name_en = ?",
                (person_name, person_name, person_name),
            ).fetchone()
            if not person:
                raise RuntimeError(f"No person record for {person_name}")
            if connection.execute("SELECT 1 FROM person_documents WHERE storage_path = ?", (str(relative),)).fetchone():
                continue
            extension = path.suffix.lower()
            document_id = str(uuid.uuid4())
            connection.execute(
                """INSERT INTO person_documents
                   (id, person_id, original_filename, stored_filename, storage_path, content_type, file_size, uploaded_by)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 'legacy-import')""",
                (document_id, person["id"], path.name, f"legacy-{document_id}{extension}", str(relative), mimetypes.guess_type(path.name)[0] or "application/octet-stream", str(path.stat().st_size)),
            )
            connection.execute(
                "UPDATE people SET id_document_status = 'received', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (person["id"],),
            )
            inserted += 1
        connection.commit()
    print(f"indexed={inserted} unassigned_or_skipped={skipped}")


if __name__ == "__main__":
    main()
