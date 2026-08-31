from copy import deepcopy

from docx import Document


PATH = "/Users/pyen/OpusFormosa/festival_planning/logistics/Steven_Lin.docx"


def values(row):
    return [cell.text.replace("\n", " ").strip() for cell in row.cells]


def set_row(row, date, time, event, venue):
    for cell, value in zip(row.cells, [date, time, event, venue]):
        cell.text = value


def find_row(table, *, date=None, event_contains=None):
    for row in table.rows:
        row_values = values(row)
        if date is not None and row_values[0] != date:
            continue
        if event_contains is not None and event_contains not in row_values[2]:
            continue
        return row
    raise RuntimeError(f"Could not find row: date={date!r}, event={event_contains!r}")


def clone_before(table, target, date, time, event, venue):
    cloned = deepcopy(target._tr)
    target._tr.addprevious(cloned)
    row = next(row for row in table.rows if row._tr is cloned)
    set_row(row, date, time, event, venue)
    return row


def clone_after(table, target, date, time, event, venue):
    cloned = deepcopy(target._tr)
    target._tr.addnext(cloned)
    row = next(row for row in table.rows if row._tr is cloned)
    set_row(row, date, time, event, venue)
    return row


document = Document(PATH)
table = document.tables[1]

# Sep 9 — Kaohsiung concert day trip with Jinjoo and Edgar.
sep9_dress = find_row(table, date="Sep 9", event_contains="Dress Rehearsal (chamber)")
clone_before(
    table, sep9_dress, "Sep 9", "~10:30",
    "HSR Taipei Main Station → Zuoying (with Jinjoo Cho and Edgar Moreau)", "HSR day trip",
)
sep9_dress.cells[0].text = ""
sep9_concert = find_row(table, event_contains="Across Generations")
clone_after(
    table, sep9_concert, "", "22:10",
    "HSR return Zuoying → Taipei Main Station (with Jinjoo Cho and Edgar Moreau)", "HSR day trip",
)

# Sep 13 — travel with Edgar for the private Taichung engagement.
sep13_private = find_row(table, date="Sep 13", event_contains="Private event in Taichung")
clone_before(
    table, sep13_private, "Sep 13", "~09:30",
    "HSR Taipei → Taichung (with Edgar Moreau)", "HSR day trip",
)
sep13_private.cells[0].text = ""
clone_after(
    table, sep13_private, "", "~14:30",
    "HSR return Taichung → Taipei (with Edgar Moreau)", "HSR day trip",
)

# Sep 14 — Taichung concert day trip with Boris and Edgar.
sep14_dress = find_row(table, date="Sep 14", event_contains="Dress Rehearsal")
clone_before(
    table, sep14_dress, "Sep 14", "Morning",
    "HSR Taipei → Taichung (with Boris Borgolotto and Edgar Moreau)", "HSR day trip",
)
sep14_dress.cells[0].text = ""
sep14_concert = find_row(table, event_contains="Chamber Series III")
clone_after(
    table, sep14_concert, "", "~22:00",
    "HSR return Taichung → Taipei (with Boris Borgolotto and Edgar Moreau)", "HSR day trip",
)

# Sep 16 — Taichung closing-concert day trip with Edgar.
sep16_dress = find_row(table, date="Sep 16", event_contains="Dress Rehearsal (chamber)")
clone_before(
    table, sep16_dress, "Sep 16", "Morning",
    "HSR Taipei → Taichung (with Edgar Moreau)", "HSR day trip",
)
sep16_dress.cells[0].text = ""
sep16_concert = find_row(table, event_contains="Opus Closing Night")
clone_after(
    table, sep16_concert, "", "~22:00",
    "HSR return Taichung → Taipei (with Edgar Moreau)", "HSR day trip",
)

expected = [
    ("Sep 9", "~10:30", "HSR Taipei Main Station → Zuoying (with Jinjoo Cho and Edgar Moreau)"),
    ("", "22:10", "HSR return Zuoying → Taipei Main Station (with Jinjoo Cho and Edgar Moreau)"),
    ("Sep 13", "~09:30", "HSR Taipei → Taichung (with Edgar Moreau)"),
    ("", "~14:30", "HSR return Taichung → Taipei (with Edgar Moreau)"),
    ("Sep 14", "Morning", "HSR Taipei → Taichung (with Boris Borgolotto and Edgar Moreau)"),
    ("", "~22:00", "HSR return Taichung → Taipei (with Boris Borgolotto and Edgar Moreau)"),
    ("Sep 16", "Morning", "HSR Taipei → Taichung (with Edgar Moreau)"),
    ("", "~22:00", "HSR return Taichung → Taipei (with Edgar Moreau)"),
]
actual = [(v[0], v[1], v[2]) for row in table.rows for v in [values(row)] if "HSR" in v[2]]
for item in expected:
    if item not in actual:
        raise RuntimeError(f"Missing expected HSR row: {item!r}")

document.save(PATH)
print("Added six Steven Lin HSR travel rows.")
