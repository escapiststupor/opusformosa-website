from pathlib import Path

from docx import Document


path = Path("/Users/pyen/OpusFormosa/festival_planning/logistics/Opus_Formosa_2026_Da_Zong_Guan_Handbook.docx")
document = Document(path)

for table in list(document.tables):
    if any("Glandys" in cell.text for row in table.rows for cell in row.cells):
        table._element.getparent().remove(table._element)

document.save(path)
