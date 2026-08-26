/** Download a Google Sheet through the current signed-in Edge profile without logging cookies. */
import { cp, mkdir, rm, writeFile } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { chromium } from 'playwright';

const [spreadsheetId, gid, output] = process.argv.slice(2);
if (!spreadsheetId || !gid || !output) throw new Error('Usage: node export_google_sheet_with_edge.mjs SPREADSHEET_ID GID OUTPUT.xlsx');

const edgeRoot = '/Users/pyen/Library/Application Support/Microsoft Edge';
const profile = 'Profile 1';
const temporaryProfile = '/private/tmp/opus-personnel-edge-profile-node';
const copyIfPresent = async (from, to) => { if (existsSync(from)) await cp(from, to); };

await rm(temporaryProfile, { recursive: true, force: true });
await mkdir(`${temporaryProfile}/${profile}`, { recursive: true });
await copyIfPresent(`${edgeRoot}/Local State`, `${temporaryProfile}/Local State`);
for (const file of ['Cookies', 'Cookies-wal', 'Cookies-shm', 'Preferences', 'Secure Preferences']) {
  await copyIfPresent(`${edgeRoot}/${profile}/${file}`, `${temporaryProfile}/${profile}/${file}`);
}

const context = await chromium.launchPersistentContext(temporaryProfile, {
  executablePath: '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
  headless: true,
  args: [`--profile-directory=${profile}`],
  ignoreDefaultArgs: ['--password-store=basic', '--use-mock-keychain'],
});
try {
  const page = await context.newPage();
  await page.goto(`https://docs.google.com/spreadsheets/d/${spreadsheetId}/edit?gid=${gid}`, { waitUntil: 'domcontentloaded', timeout: 30_000 });
  if (page.url().includes('accounts.google.com')) throw new Error('Edge profile is not signed in to Google for this Sheet.');
  const response = await context.request.get(`https://docs.google.com/spreadsheets/d/${spreadsheetId}/export?format=xlsx&gid=${gid}`, { timeout: 30_000 });
  if (!response.ok()) throw new Error(`Google Sheet export failed with HTTP ${response.status()}.`);
  await writeFile(output, await response.body());
  console.log(`exported_workbook=${output}`);
} finally {
  await context.close();
}
