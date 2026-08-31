from pathlib import Path

from docx import Document


base = Path('/Users/pyen/OpusFormosa/festival_planning/logistics')
for name in ['Jinjoo_Cho.docx', 'Kyu_Yeon_Kim.docx', 'Brannon_Cho.docx']:
    document = Document(base / name)
    table = next(
        table for table in document.tables
        if [cell.text.strip() for cell in table.rows[0].cells][:2] == ['Date', 'Time']
    )
    print(f'--- {name}')
    current_date = ''
    for row in table.rows[1:]:
        values = [cell.text.replace('\n', ' / ').strip() for cell in row.cells]
        current_date = values[0] or current_date
        if any('CHR' in value for value in values):
            values[0] = current_date
            print(' | '.join(values))
