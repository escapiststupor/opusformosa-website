from copy import deepcopy
from pathlib import Path

from docx import Document


path = Path('/Users/pyen/OpusFormosa/festival_planning/logistics/Jinjoo_Cho.docx')
doc = Document(path)
table = next(table for table in doc.tables if [cell.text.strip() for cell in table.rows[0].cells][:2] == ['Date', 'Time'])

if any('HSR to Kaohsiung' in cell.text for row in table.rows for cell in row.cells):
    raise RuntimeError('Jinjoo HSR travel is already present')

def values(row):
    return [cell.text.strip() for cell in row.cells]

def set_values(row, items):
    for cell, item in zip(row.cells, items):
        cell.text = item

chamber_index = next(
    index for index, row in enumerate(table.rows)
    if values(row)[0] == 'Sep 9' and values(row)[1] == '13:00–15:00'
)
chamber_row = table.rows[chamber_index]
outbound_xml = deepcopy(chamber_row._tr)
table._tbl.insert(chamber_index, outbound_xml)
outbound_row = table.rows[chamber_index]
set_values(outbound_row, [
    'Sep 9', '~10:30',
    'HSR to Kaohsiung (Taipei Main Station → Zuoying, with Edgar Moreau)',
    'HSR day trip',
])

current_date = ''
concert_index = None
for index, row in enumerate(table.rows):
    row_values = values(row)
    if row_values[0]:
        current_date = row_values[0]
    if current_date == 'Sep 9' and row_values[1] == '19:30':
        concert_index = index
        break
if concert_index is None:
    raise RuntimeError('Sep 9 concert row was not found')
concert_row = table.rows[concert_index]
return_xml = deepcopy(concert_row._tr)
table._tbl.insert(concert_index + 1, return_xml)
return_row = table.rows[concert_index + 1]
set_values(return_row, [
    '', '22:10',
    'HSR return Zuoying → Taipei (taxi to hotel, with Edgar Moreau)',
    'HSR',
])

doc.save(path)
print(path)
