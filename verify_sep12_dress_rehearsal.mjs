import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const workbookPath = "outputs/opus_schedule_update/Opus_Formosa_2026_Rehearsal_Schedule_UPDATED.xlsx";
const input = await FileBlob.load(workbookPath);
const workbook = await SpreadsheetFile.importXlsx(input);

const master = workbook.worksheets.getItem("Master Schedule");
const booking = workbook.worksheets.getItem("Room Booking");
console.log(JSON.stringify({
  masterSep12Morning: master.getRange("B12").values[0][0],
  masterSep13Morning: master.getRange("B13").values[0][0],
  roomBookingSep12: booking.getRange("E35").values[0][0],
}));

const scan = await workbook.inspect({
  kind: "match",
  sheetId: "Master Schedule",
  range: "A1:E16",
  searchTerm: "Dress Rehearsal 09:30–12:00|Sep 13",
  options: { useRegex: true, maxResults: 30 },
  maxChars: 3000,
});
console.log(scan.ndjson);

const formulaErrors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 100 },
  maxChars: 3000,
});
console.log(formulaErrors.ndjson);

const outputDir = "/private/tmp/excel_schedule_final_review";
await fs.rm(outputDir, { recursive: true, force: true });
await fs.mkdir(outputDir, { recursive: true });
for (const worksheet of workbook.worksheets.items) {
  const preview = await workbook.render({ sheetName: worksheet.name, autoCrop: "all", scale: 1, format: "png" });
  await fs.writeFile(`${outputDir}/${worksheet.name.replaceAll(" ", "_")}.png`, new Uint8Array(await preview.arrayBuffer()));
}
console.log(outputDir);
