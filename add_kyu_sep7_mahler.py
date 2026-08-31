from copy import deepcopy
from pathlib import Path

from docx import Document
from docx.table import _Row


path = Path('/Users/pyen/OpusFormosa/festival_planning/logistics/Kyu_Yeon_Kim.docx')
document = Document(path)
schedule = next(
    table for table in document.tables
    if [cell.text.strip() for cell in table.rows[0].cells][:2] == ['Date', 'Time']
)

if any(
    row.cells[1].text.strip() == '13:00–15:00'
    and row.cells[2].text.strip() == 'Mahler: Piano Quartet in A minor'
    and row.cells[3].text.strip() == 'CHR4'
    for row in schedule.rows
):
    raise RuntimeError('The Sep 7 Mahler rehearsal is already present.')

template = next(
    row for row in schedule.rows
    if row.cells[1].text.strip() == '13:00–15:00'
    and row.cells[2].text.strip() == 'Ravel: Piano Trio in A minor'
)
practice = next(
    row for row in schedule.rows
    if row.cells[1].text.strip() == '16:00–19:00'
    and 'Practice room' in row.cells[2].text
)

new_tr = deepcopy(template._tr)
new_row = _Row(new_tr, schedule)
new_row.cells[0].text = ''
new_row.cells[1].text = '13:00–15:00'
new_row.cells[2].text = 'Mahler: Piano Quartet in A minor'
new_row.cells[3].text = 'CHR4'
practice._tr.addprevious(new_tr)

document.save(path)
print(path)
