import { FileBlob, SpreadsheetFile } from '@oai/artifact-tool';
const wb = await SpreadsheetFile.importXlsx(await FileBlob.load('/private/tmp/opus_formosa_2026_source.xlsx'));
const sheet = wb.worksheets.getItem('Individual Schedules');
console.log(sheet.tables.items.map(t => ({ name: t.name, range: t.range?.address })));
