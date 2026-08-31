from pathlib import Path

from docx import Document


ROOT = Path('/Users/pyen/OpusFormosa/festival_planning/logistics')


for path in sorted(ROOT.glob('*.docx')):
    doc = Document(path)
    for table_index, table in enumerate(doc.tables):
        for row_index, row in enumerate(table.rows):
            cells = [cell.text.replace('\n', ' | ') for cell in row.cells]
            if any('HSR' in cell for cell in cells):
                print(path.name, table_index, row_index, ' || '.join(cells))
