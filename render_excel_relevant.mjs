import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const input = await FileBlob.load("outputs/opus_schedule_update/Opus_Formosa_2026_Rehearsal_Schedule_UPDATED.xlsx");
const workbook = await SpreadsheetFile.importXlsx(input);
await fs.mkdir("/private/tmp/excel_schedule_review", { recursive: true });

for (const [sheetName, range] of [
  ["Master Schedule", "A1:E16"],
  ["Room Booking", "A30:H38"],
]) {
  const image = await workbook.render({ sheetName, range, scale: 2, format: "png" });
  await fs.writeFile(`/private/tmp/excel_schedule_review/${sheetName.replaceAll(" ", "_")}.png`, new Uint8Array(await image.arrayBuffer()));
}
