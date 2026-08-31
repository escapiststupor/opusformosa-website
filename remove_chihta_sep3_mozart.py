from docx import Document


PATH = "/Users/pyen/OpusFormosa/festival_planning/logistics/Chih-Ta_Chen.docx"

document = Document(PATH)
removed = []

for table_number, table in enumerate(document.tables):
    for row_number in range(len(table.rows) - 1, -1, -1):
        row = table.rows[row_number]
        cells = [cell.text.replace("\n", " ").strip() for cell in row.cells]
        if (
            len(cells) >= 4
            and cells[0] == "Sep 3"
            and cells[1] == "15:00–17:00"
            and cells[2] == "Mozart: Duo for Violin and Viola K.423"
            and cells[3] == "CHR3"
        ):
            removed.append((table_number, row_number, cells))
            table._tbl.remove(row._tr)

if len(removed) != 1:
    raise RuntimeError(f"Expected exactly one incorrect Sep 3 Mozart row; found {removed!r}")

document.save(PATH)
print("Removed:", removed)
