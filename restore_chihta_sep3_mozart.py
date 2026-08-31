from copy import deepcopy

from docx import Document


PATH = "/Users/pyen/OpusFormosa/festival_planning/logistics/Chih-Ta_Chen.docx"

document = Document(PATH)
table = document.tables[1]

# Reuse the existing Sep 5 Mozart row so the restored row retains the handbook's
# schedule-table geometry and formatting.
template = next(
    row for row in table.rows
    if row.cells[0].text.strip() == "Sep 5"
    and row.cells[2].text.strip() == "Mozart: Duo for Violin and Viola K.423"
)
new_tr = deepcopy(template._tr)

# Insert immediately before the 9/3 Shostakovich evening row.
target = next(
    row for row in table.rows
    if row.cells[1].text.strip() == "19:15–21:45"
    and "Shostakovich" in row.cells[2].text
)
target._tr.addprevious(new_tr)

# Retrieve the just-inserted row and set its values.
restored = next(
    row for row in table.rows
    if row._tr is new_tr
)
values = [
    "Sep 3",
    "15:00–17:00",
    "Mozart: Duo for Violin and Viola K.423",
    "CHR3",
]
for cell, value in zip(restored.cells, values):
    cell.text = value

matches = [
    row for row in table.rows
    if row.cells[0].text.strip() == "Sep 3"
    and row.cells[1].text.strip() == "15:00–17:00"
    and row.cells[2].text.strip() == "Mozart: Duo for Violin and Viola K.423"
    and row.cells[3].text.strip() == "CHR3"
]
if len(matches) != 1:
    raise RuntimeError(f"Expected one restored Sep 3 Mozart row; found {len(matches)}")

document.save(PATH)
print("Restored Sep 3 Afternoon 2 Mozart row.")
