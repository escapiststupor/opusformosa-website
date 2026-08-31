from copy import deepcopy
from pathlib import Path

from docx import Document


SOURCE = Path('/Users/pyen/OpusFormosa/festival_planning/logistics/Kyu_Yeon_Kim.docx')
OUTPUT = Path('/private/tmp/kyu_schedule_update/Kyu_Yeon_Kim.docx')


def set_row(row, values):
    for cell, value in zip(row.cells, values):
        cell.text = value


def insert_before(table, target_row, values):
    new_tr = deepcopy(table.rows[1]._tr)  # Existing ordinary rehearsal-row formatting.
    table._tbl.insert(table._tbl.index(target_row._tr), new_tr)
    inserted = next(row for row in table.rows if row._tr is new_tr)
    set_row(inserted, values)
    return inserted


def find_row(table, date, time):
    for row in table.rows:
        values = [cell.text.strip() for cell in row.cells]
        if values[0] == date and values[1] == time:
            return row
    raise ValueError(f'Could not find {date} {time}')


def main():
    doc = Document(SOURCE)
    table = doc.tables[1]

    # Insert each personal practice slot in chronological order and retain the
    # original schedule table and rehearsal/concert formatting.
    target = find_row(table, 'Sep 7', '13:00–15:00')
    insert_before(table, target, ['Sep 7', '10:00–12:00', 'Practice room — grand piano', 'Kawaii Studio'])
    target.cells[0].text = ''
    target = find_row(table, 'Sep 8', '13:00–15:00')
    insert_before(table, target, ['Sep 8', '10:00–12:00', 'Practice room — grand piano', 'Kawaii Studio'])
    target.cells[0].text = ''
    target = find_row(table, 'Sep 9', '13:00–15:00')
    insert_before(table, target, ['', '16:00–19:00', 'Practice room — grand piano', 'Kawaii Studio'])

    target = find_row(table, 'Sep 9', '13:00–15:00')
    insert_before(table, target, ['Sep 9', '10:00–12:00', 'Practice room — grand piano', 'Kawaii Studio'])
    target.cells[0].text = ''

    target = find_row(table, 'Sep 10', '13:00–15:00')
    insert_before(table, target, ['Sep 10', '10:00–12:00', 'Practice room — grand piano', 'Kawaii Studio'])
    target.cells[0].text = ''

    target = find_row(table, 'Sep 11', '19:30–21:30')
    insert_before(table, target, ['Sep 11', '10:00–12:00', 'Practice room — grand piano', 'Kawaii Studio'])
    insert_before(table, target, ['', '14:00–18:00', 'Practice room — upright piano', 'Kawaii Studio'])
    target.cells[0].text = ''

    target = find_row(table, 'Sep 12', '09:30–12:00')
    concert = next(row for row in table.rows if row.cells[1].text.strip() == '19:30' and 'Chamber Series II' in row.cells[2].text)
    insert_before(table, concert, ['', '14:00–17:00', 'Practice room — grand piano', 'Kawaii Studio'])

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(OUTPUT)


if __name__ == '__main__':
    main()
