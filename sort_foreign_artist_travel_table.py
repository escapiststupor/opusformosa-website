import re

from docx import Document


PATH = "/Users/pyen/OpusFormosa/festival_planning/logistics/Opus_Formosa_2026_Da_Zong_Guan_Handbook.docx"
TABLE_INDEX = 2


def chronological_key(row):
    text = row.cells[0].text
    match = re.search(r"9月\s*(\d+)\s+(\d{1,2}):(\d{2})", text)
    if not match:
        raise ValueError(f"Could not parse travel time: {text!r}")
    day, hour, minute = map(int, match.groups())
    return day, hour, minute


document = Document(PATH)
table = document.tables[TABLE_INDEX]
header, *rows = table.rows

for row in sorted(rows, key=chronological_key):
    table._tbl.remove(row._tr)
    table._tbl.append(row._tr)

document.save(PATH)
print("Sorted foreign artist travel and hotel management table chronologically.")
