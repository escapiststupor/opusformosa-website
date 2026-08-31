from copy import deepcopy
from pathlib import Path

from docx import Document


path = Path('/Users/pyen/OpusFormosa/festival_planning/logistics/Jinjoo_Cho.docx')
doc = Document(path)
table = next(table for table in doc.tables if [cell.text.strip() for cell in table.rows[0].cells][:2] == ['Date', 'Time'])
if len(table.rows) != 14:
    raise RuntimeError(f'Unexpected schedule row count: {len(table.rows)}')

rows = table.rows
style_templates = {
    'normal': [deepcopy(cell._tc.tcPr) for cell in rows[2].cells],
    'concert': [deepcopy(cell._tc.tcPr) for cell in rows[4].cells],
    'dress': [deepcopy(cell._tc.tcPr) for cell in rows[5].cells],
}


def set_row(index, values, style_name=None):
    target = rows[index]
    if style_name is not None:
        for template, cell in zip(style_templates[style_name], target.cells):
            target_pr = cell._tc.tcPr
            if target_pr is not None:
                cell._tc.remove(target_pr)
            if template is not None:
                cell._tc.insert(0, deepcopy(template))
    for cell, value in zip(target.cells, values):
        cell.text = value


set_row(1, ['Sep 8', '13:00–15:00', 'Ravel: Piano Trio in A minor', 'CHR4'], 'normal')
set_row(2, ['', '15:00–17:00', 'Rachmaninoff: Trio élégiaque No.1', 'CHR4'], 'normal')
set_row(3, ['Sep 9', '~10:30', 'HSR to Kaohsiung (Taipei Main Station → Zuoying, with Edgar Moreau)', 'HSR day trip'], 'normal')
set_row(4, ['', '13:00–15:00', 'Dress Rehearsal (chamber)', 'Weiwuying Concert Hall'], 'dress')
set_row(5, ['', '19:30', '★ CONCERT — Across Generations', 'Weiwuying Concert Hall'], 'concert')
set_row(6, ['', '22:10', 'HSR return: Zuoying → Taipei Main Station (with Edgar Moreau)', 'HSR day trip'], 'normal')
set_row(7, ['Sep 10', '13:00–15:00', 'Dress Rehearsal', 'Taipei Recital Hall'], 'dress')
set_row(8, ['', '15:00–17:00', 'Dress Rehearsal', 'Taipei Recital Hall'], 'dress')
set_row(9, ['', '19:30', '★ CONCERT — Chamber Series I', 'Taipei Recital Hall'], 'concert')
set_row(10, ['Sep 11', '13:00–15:00', 'Tchaikovsky: String Sextet', 'CHR4'], 'normal')
set_row(11, ['', '15:00–17:00', 'Tchaikovsky: String Sextet', 'CHR4'], 'normal')
set_row(12, ['Sep 12', '09:30–12:00', 'Dress Rehearsal', 'Taipei Recital Hall'], 'dress')
set_row(13, ['', '19:30', '★ CONCERT — Chamber Series II', 'Taipei Recital Hall'], 'concert')

doc.save(path)
print(path)
