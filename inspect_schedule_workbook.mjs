import fs from 'node:fs/promises';
import { FileBlob, SpreadsheetFile } from '@oai/artifact-tool';

const source = '/private/tmp/opus_formosa_2026_source.xlsx';
const outDir = '/private/tmp/opus_schedule_inspect';
await fs.mkdir(outDir, { recursive: true });
const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(source));
console.log((await workbook.inspect({
  kind: 'workbook,sheet,table', maxChars: 10000, tableMaxRows: 12, tableMaxCols: 6,
})).ndjson);
for (const sheet of workbook.worksheets.items) {
  const preview = await workbook.render({ sheetName: sheet.name, autoCrop: 'all', scale: 0.7, format: 'png' });
  await fs.writeFile(`${outDir}/${sheet.name.replaceAll('/', '-')}.png`, new Uint8Array(await preview.arrayBuffer()));
}
