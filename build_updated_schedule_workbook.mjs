import fs from 'node:fs/promises';
import { FileBlob, SpreadsheetFile } from '@oai/artifact-tool';

const sourcePath = '/private/tmp/opus_formosa_2026_source.xlsx';
const outputDir = '/Users/pyen/OpusFormosa/website/outputs/opus_schedule_update';
const outputPath = `${outputDir}/Opus_Formosa_2026_Rehearsal_Schedule_UPDATED.xlsx`;
const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(sourcePath));

const individual = workbook.worksheets.getItem('Individual Schedules');
const maxInitialRow = 276;
const matrix = individual.getRange(`A1:E${maxInitialRow}`).values;

function rowText(row) {
  return row.map(value => String(value ?? '')).join(' | ');
}

function locateEntries() {
  const entries = [];
  let player = '';
  let date = '';
  for (let index = 0; index < matrix.length; index += 1) {
    const row = matrix[index].map(value => String(value ?? ''));
    const [first, session, time, event, venue] = row;
    if (first && !session && !time && !event && !venue) {
      player = first;
      date = '';
      continue;
    }
    if (first === 'Date' && session === 'Session') {
      date = '';
      continue;
    }
    if (first) date = first;
    if (player && date && time && event) entries.push({ row: index + 1, player, date, session, time, event, venue });
  }
  return entries;
}

let entries = locateEntries();
const find = (player, date, predicate) => {
  const matches = entries.filter(entry => entry.player === player && entry.date === date && predicate(entry));
  if (matches.length !== 1) throw new Error(`Expected one match for ${player} ${date}; found ${matches.length}`);
  return matches[0];
};

// Apply confirmed times in individual schedules.
const shostakovichPlayers = ['Steven Lin', 'Sirena Huang', 'Eugene Lin', 'Chih-Ta Chen', 'Hou Chuan-An  (Trumpet)'];
const dvorakPlayers = ['Steven Lin', 'Adrien La Marca', 'Boris Borgolotto', 'Edgar Moreau', 'Belle Ting'];
const sep12Players = ['Sirena Huang', 'Eugene Lin', 'Adrien La Marca', 'Boris Borgolotto', 'Jinjoo Cho', 'Brannon Cho', 'Kyuyeon Kim', 'Edgar Moreau', 'Chih-Ta Chen'];
for (const player of shostakovichPlayers) {
  const entry = find(player, 'Sep 3', e => e.event.includes('Shostakovich'));
  matrix[entry.row - 1][2] = '19:15–21:45';
}
for (const player of dvorakPlayers) {
  const entry = find(player, 'Sep 8', e => e.event.includes('Dvořák'));
  matrix[entry.row - 1][2] = '19:00–21:30';
}
for (const player of sep12Players) {
  const entry = find(player, 'Sep 12', e => e.event.startsWith('Dress Rehearsal'));
  matrix[entry.row - 1][2] = '09:30–12:00';
}

// On Sep 10, only that evening's Taipei Recital Hall performers rehearse 13:00–15:00.
const sep10Performers = ['Adrien La Marca', 'Belle Ting', 'Boris Borgolotto', 'Brannon Cho', 'Edgar Moreau', 'Jinjoo Cho', 'Kyuyeon Kim', 'Steven Lin'];
const dressEvent = 'Dress Rehearsal (Taipei Recital Hall)';
const dressVenue = 'Taipei Recital Hall';
const toInsert = [];
for (const player of sep10Performers) {
  const existing = entries.filter(e => e.player === player && e.date === 'Sep 10' && e.time === '13:00–15:00');
  if (existing.length === 1) {
    matrix[existing[0].row - 1][3] = dressEvent;
    matrix[existing[0].row - 1][4] = dressVenue;
  } else if (existing.length === 0) {
    const afternoon2 = find(player, 'Sep 10', e => e.time === '15:00–17:00');
    toInsert.push({ player, row: afternoon2.row });
  } else {
    throw new Error(`Unexpected duplicate Sep 10 afternoon rehearsal for ${player}`);
  }
}
// Granados was removed from this Sep 10 slot: those two people do not perform that evening.
for (const player of ['Chih-Ta Chen', 'Sophie Wang']) {
  const cancelled = find(player, 'Sep 10', e => e.time === '13:00–15:00' && e.event.includes('Granados'));
  matrix[cancelled.row - 1] = ['', '', '', '', ''];
}

// Shift lower rows downward (including their formats) to make chronological rows for four performers.
// Work bottom-up so source row numbers remain valid.
let lastRow = maxInitialRow;
for (const item of [...toInsert].sort((a, b) => b.row - a.row)) {
  const source = individual.getRange(`A${item.row}:E${lastRow}`);
  const destination = individual.getRange(`A${item.row + 1}:E${lastRow + 1}`);
  destination.copyFrom(source, 'all');
  matrix.splice(item.row - 1, 0, ['Sep 10', 'Afternoon 1', '13:00–15:00', dressEvent, dressVenue]);
  lastRow += 1;
}

// Rewrite values only; copyFrom above has kept all existing formatting aligned with moved rows.
individual.getRange(`A1:E${lastRow}`).values = matrix.slice(0, lastRow);

// Keep the master schedule's displayed timing synchronized where the time is embedded in the cell.
const master = workbook.worksheets.getItem('Master Schedule');
master.getRange('E9').values = [[
  '19:00–21:30 Dvořák: Piano Quintet Op.81 (CHR4)\n  Belle Ting, Boris Borgolotto, Adrien La Marca, Edgar Moreau, Steven Lin',
]];
master.getRange('B13').values = [[
  'Dress Rehearsal 09:30–12:00 (Taipei Recital Hall)\n  All Sep 12 performers',
]];

await fs.mkdir(outputDir, { recursive: true });
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);

const individualCheck = await workbook.inspect({
  kind: 'match',
  searchTerm: '19:15–21:45|19:00–21:30|09:30–12:00|Dress Rehearsal \\(Taipei Recital Hall\\)',
  options: { useRegex: true, maxResults: 100 },
  summary: 'confirmed schedule updates',
});
console.log(individualCheck.ndjson);
const errors = await workbook.inspect({
  kind: 'match', searchTerm: '#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A',
  options: { useRegex: true, maxResults: 50 }, summary: 'formula errors',
});
console.log(errors.ndjson);

for (const sheet of workbook.worksheets.items) {
  const preview = await workbook.render({ sheetName: sheet.name, autoCrop: 'all', scale: 0.7, format: 'png' });
  await fs.writeFile(`${outputDir}/${sheet.name.replaceAll('/', '-')}.png`, new Uint8Array(await preview.arrayBuffer()));
}
console.log(`output=${outputPath}`);
