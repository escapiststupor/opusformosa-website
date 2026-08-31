import csv
import re
from collections import defaultdict
from pathlib import Path

from docx import Document


CSV_PATH = Path('/private/tmp/opus_individual_schedules.csv')
DOC_ROOT = Path('/Users/pyen/OpusFormosa/festival_planning/logistics')


def name_key(value):
    return re.sub(r'[^a-z0-9]', '', value.lower().replace('trumpet', ''))


def clean(value):
    value = value.replace('★', '').replace('@', '').replace('(CHR1)', '').replace('(CHR2)', '').replace('(CHR3)', '').replace('(CHR4)', '')
    value = value.replace('(Taipei Concert Hall)', '').replace('(Taipei Recital Hall)', '').replace('(Weiwuying Concert Hall)', '')
    value = value.replace('  ', ' ').strip().lower()
    return re.sub(r'[^a-z0-9]+', ' ', value).strip()


def parse_sheet():
    schedules = defaultdict(list)
    player = None
    active = False
    current_date = None
    with CSV_PATH.open(newline='') as fh:
        for row in csv.reader(fh):
            row += [''] * (5 - len(row))
            first, date, session, time, event = row[:5]
            venue = row[4] if len(row) == 5 else ''
            # A player heading has only the first cell populated.
            if first and not any(row[1:5]):
                player = first
                active = False
                current_date = None
                continue
            if first == 'Date' and row[1] == 'Session':
                active = True
                current_date = None
                continue
            if not active or not player:
                continue
            if first:
                current_date = first
            if current_date and row[2] and row[3]:
                schedules[name_key(player)].append({
                    'date': current_date,
                    'time': row[2],
                    'event': row[3],
                    'venue': row[4],
                })
    return schedules


def parse_doc(path):
    doc = Document(path)
    for table in doc.tables:
        if not table.rows or len(table.rows[0].cells) < 4:
            continue
        headers = [cell.text.strip().lower() for cell in table.rows[0].cells]
        if headers[:2] != ['date', 'time'] or 'programme / event' not in headers[2]:
            continue
        entries = []
        current_date = None
        for row in table.rows[1:]:
            cells = [cell.text.strip() for cell in row.cells]
            if cells[0]:
                current_date = cells[0]
            if current_date and len(cells) >= 4 and cells[1] and cells[2]:
                entries.append({'date': current_date, 'time': cells[1], 'event': cells[2], 'venue': cells[3]})
        return entries
    return []


def is_logistics_only(entry):
    return any(token in entry['event'].lower() for token in ('airport arrival', 'priority hotel check-in', 'shared taxi', 'practice room'))


def main():
    sheet = parse_sheet()
    docs = {}
    for path in DOC_ROOT.glob('*.docx'):
        entries = parse_doc(path)
        if entries:
            docs[name_key(path.stem)] = (path.name, entries)

    print('SHEET_PLAYERS_NOT_IN_DOCS')
    for key in sorted(set(sheet) - set(docs)):
        print(key)
    print('\nDOC_PLAYERS_NOT_IN_SHEET')
    for key, (name, _) in sorted(docs.items()):
        if key not in sheet:
            print(name)

    print('\nDATE_TIME_DIFFS')
    for key in sorted(set(sheet) & set(docs)):
        filename, doc_entries = docs[key]
        doc_core = [e for e in doc_entries if not is_logistics_only(e)]
        sheet_by_key = {(e['date'], e['time']): e for e in sheet[key]}
        doc_by_key = {(e['date'], e['time']): e for e in doc_core}
        missing = [e for k, e in sheet_by_key.items() if k not in doc_by_key]
        extra = [e for k, e in doc_by_key.items() if k not in sheet_by_key]
        if missing or extra:
            print('\n' + filename)
            for e in missing:
                print('  MISSING_FROM_DOC:', e['date'], '|', e['time'], '|', e['event'], '|', e['venue'])
            for e in extra:
                print('  EXTRA_OR_TIME_CHANGED:', e['date'], '|', e['time'], '|', e['event'], '|', e['venue'])

    print('\nSAME_DATE_TIME_EVENT_VENUE_DIFFS')
    for key in sorted(set(sheet) & set(docs)):
        filename, doc_entries = docs[key]
        doc_core = [e for e in doc_entries if not is_logistics_only(e)]
        sheet_by_key = {(e['date'], e['time']): e for e in sheet[key]}
        for e in doc_core:
            other = sheet_by_key.get((e['date'], e['time']))
            if other and (clean(e['event']) != clean(other['event']) or clean(e['venue']) != clean(other['venue'])):
                print(filename, '|', e['date'], e['time'], '| DOC:', e['event'], '/', e['venue'], '| SHEET:', other['event'], '/', other['venue'])


if __name__ == '__main__':
    main()
