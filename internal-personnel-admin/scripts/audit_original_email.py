#!/usr/bin/env python3
"""Audit the original festival-coordination email against the personnel database."""

from __future__ import annotations

import argparse
import sqlite3


PEOPLE = {
    "陳逸庭", "鄒佳宏", "黃凱珉", "李騏", "曾婕安", "張頌奇", "徐溢恩", "黃培禎", "張仲薇",
    "陳志達", "黃亞漢", "蕭佳倩", "林恩俊", "楊舜名", "劉哲川", "連珮致", "賴柏融", "侯傳安",
    "阮黃松", "張鄭立", "劉品均", "黃哲筠", "江國安", "陳婷怡", "陳凱馨", "呂少評", "巨彥博",
    "陳玥絨", "黃俊綸", "許夢芬", "林易", "王子欣", "黃慈恩", "馬竟家", "丁章媛",
    "Aimi Sorita", "Adrien La Marca", "Boris Borgolotto", "Jinjoo Cho", "Edgar Moreau", "Kyu Yeon Kim", "Brannon Cho", "嚴子晴",
}
EXPECTED_VALUES = {
    "江國安": {"id_document_number": "G122079159", "birth_date": "1980-12-17"},
    "陳婷怡": {"id_document_number": "F231378719", "birth_date": "1988-08-08"},
    "巨彥博": {"id_document_number": "A125995761", "birth_date": "1988-08-02"},
    "陳玥絨": {"id_document_number": "H225168610", "birth_date": "1998", "phone": "0984108391"},
    "黃俊綸": {"id_document_number": "Q124001307", "birth_date": "1991-12-06"},
    "許夢芬": {"id_document_number": "H224183408", "birth_date": "1992-12-28"},
    "林易": {"id_document_number": "F800208677", "birth_date": "1989-03-25"},
    "黃慈恩": {"email": "ambercute2006@icloud.com", "phone": "0905018271", "id_document_number": "L225944087", "birth_date": "1995-10-29"},
    "馬竟家": {"email": "jingjiama520@gmail.com", "phone": "0965525393", "id_document_number": "L126012608", "birth_date": "2007-09-10"},
    "丁章媛": {"id_document_number": "A230394232", "birth_date": "2000-05-05"},
}
EXPECTED_ROLES = {
    "江國安": "錄音師", "陳婷怡": "江國安錄音助理", "呂少評": "舞台監督", "巨彥博": "台中兩場打雜工",
    "陳玥絨": "高雄攝影師", "黃俊綸": "其他場次攝影師", "許夢芬": "黃俊綸攝影助理",
    "林易": "鋼琴", "王子欣": "小提琴", "黃慈恩": "台中場工讀", "馬竟家": "台中場工讀", "丁章媛": "小提琴",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("database")
    args = parser.parse_args()
    missing_people: list[str] = []
    missing_values: list[str] = []
    missing_roles: list[str] = []
    with sqlite3.connect(args.database) as connection:
        connection.row_factory = sqlite3.Row
        records = {}
        for row in connection.execute("SELECT * FROM people"):
            record = dict(row)
            for name in (record["display_name"], record["legal_name_zh"], record["legal_name_en"]):
                if name:
                    records[str(name)] = record
        for name in sorted(PEOPLE):
            if name not in records:
                missing_people.append(name)
        for name, values in EXPECTED_VALUES.items():
            record = records.get(name)
            if not record:
                continue
            for field, expected in values.items():
                if str(record.get(field) or "") != expected:
                    missing_values.append(f"{name}:{field}")
        for name, role in EXPECTED_ROLES.items():
            record = records.get(name)
            if not record:
                continue
            roles = {row[0] for row in connection.execute("SELECT role_name FROM person_roles WHERE person_id = ?", (record["id"],))}
            if role not in roles:
                missing_roles.append(f"{name}:{role}")
    print(f"missing_people={len(missing_people)} missing_values={len(missing_values)} missing_roles={len(missing_roles)}")
    for label, values in (("people", missing_people), ("values", missing_values), ("roles", missing_roles)):
        if values:
            print(f"{label}:" + ",".join(values))


if __name__ == "__main__":
    main()
