import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const inputPath = "outputs/opus_schedule_update/Opus_Formosa_2026_Rehearsal_Schedule_UPDATED.xlsx";
const input = await FileBlob.load(inputPath);
const workbook = await SpreadsheetFile.importXlsx(input);

const sheet = workbook.worksheets.getItem("Individual Schedules");
const review = await workbook.inspect({
  kind: "table,match",
  sheetId: "Individual Schedules",
  range: "A1:G260",
  searchTerm: "Sep 13|Dress Rehearsal|09:30",
  options: { useRegex: true, maxResults: 200 },
  tableMaxRows: 260,
  tableMaxCols: 7,
  tableMaxCellChars: 100,
  maxChars: 18000,
});
console.log(review.ndjson);

const values = sheet.getRange("A1:G260").values;
for (let row = 0; row < values.length; row += 1) {
  const rowValues = values[row];
  if (rowValues.some((value) => String(value ?? "").includes("Sep 13"))) {
    console.log(`ROW ${row + 1}: ${JSON.stringify(rowValues)}`);
  }
}

console.log("--- ALL SHEETS: rows containing Sep 13 / 09:30 / Dress Rehearsal");
for (const candidate of workbook.worksheets.items) {
  const used = candidate.getUsedRange();
  const candidateValues = used.values;
  for (let row = 0; row < candidateValues.length; row += 1) {
    const joined = candidateValues[row].map((value) => String(value ?? "")).join(" | ");
    if (joined.includes("Sep 13") || joined.includes("09:30") || joined.includes("Dress Rehearsal")) {
      console.log(`${candidate.name} row ${row + 1}: ${joined}`);
    }
  }
}
