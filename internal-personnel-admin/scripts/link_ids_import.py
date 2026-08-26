#!/usr/bin/env python3
"""Mark people with a named document from the 2026-08-25 ID import as received."""

from __future__ import annotations

import argparse
import sqlite3


NAMES = (
    "陳逸庭", "林易", "李騏", "劉品均", "連珮致", "黃哲筠", "徐溢恩", "劉哲川",
    "曾婕安", "張頌奇", "侯傳安", "鄒佳宏", "劉虹麟", "蕭佳倩", "張仲薇", "丁章媛",
    "陳志達", "柯曉慧", "曾柏雄",
)
SOURCE_NOTE = "已收到證件影像，待核驗；檔案：Fly 私有磁碟 /data/personnel-documents/imports/ids-2026-08-25/IDs"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("database")
    args = parser.parse_args()
    with sqlite3.connect(args.database) as connection:
        changed = 0
        for name in NAMES:
            result = connection.execute(
                """UPDATE people SET id_document_status = 'received', id_document_note = ?
                   WHERE display_name = ? OR legal_name_zh = ?""",
                (SOURCE_NOTE, name, name),
            )
            changed += result.rowcount
        print(f"linked={changed} expected={len(NAMES)}")


if __name__ == "__main__":
    main()
