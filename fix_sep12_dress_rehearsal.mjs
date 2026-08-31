import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const workbookPath = "outputs/opus_schedule_update/Opus_Formosa_2026_Rehearsal_Schedule_UPDATED.xlsx";
const input = await FileBlob.load(workbookPath);
const workbook = await SpreadsheetFile.importXlsx(input);

const master = workbook.worksheets.getItem("Master Schedule");
const sep12Morning = master.getRange("B12");
const sep13Morning = master.getRange("B13");

if (!String(sep12Morning.values[0][0]).includes("09:00–12:00")) {
  throw new Error(`Unexpected Master Schedule B12 value: ${sep12Morning.values[0][0]}`);
}
if (!String(sep13Morning.values[0][0]).includes("09:30–12:00")) {
  throw new Error(`Unexpected Master Schedule B13 value: ${sep13Morning.values[0][0]}`);
}

sep12Morning.values = [["Dress Rehearsal 09:30–12:00 (Taipei Recital Hall)\nAll Sep 12 performers"]];
sep13Morning.clear({ applyTo: "contents" });

const roomBooking = workbook.worksheets.getItem("Room Booking");
const bookingTime = roomBooking.getRange("E35");
if (bookingTime.values[0][0] !== "09:00–12:00") {
  throw new Error(`Unexpected Room Booking E35 value: ${bookingTime.values[0][0]}`);
}
bookingTime.values = [["09:30–12:00"]];

const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(workbookPath);
console.log(workbookPath);
