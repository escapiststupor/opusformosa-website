"""Download one shared Google Sheet tab using the currently signed-in Edge profile.

The script copies only Edge's encrypted cookie files into a temporary profile. It never
prints cookies or spreadsheet contents. The exported workbook is written to /private/tmp
for read-only import validation.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from playwright.sync_api import sync_playwright


EDGE_USER_DATA = Path("/Users/pyen/Library/Application Support/Microsoft Edge")
EDGE_PROFILE = "Profile 1"
TEMP_PROFILE = Path("/private/tmp/opus-personnel-edge-profile")
EDGE_BINARY = "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"


def copy_if_present(source: Path, destination: Path) -> None:
    if source.exists():
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def prepare_profile() -> None:
    shutil.rmtree(TEMP_PROFILE, ignore_errors=True)
    TEMP_PROFILE.mkdir(parents=True)
    copy_if_present(EDGE_USER_DATA / "Local State", TEMP_PROFILE / "Local State")
    for name in ("Cookies", "Cookies-wal", "Cookies-shm", "Preferences", "Secure Preferences"):
        copy_if_present(EDGE_USER_DATA / EDGE_PROFILE / name, TEMP_PROFILE / EDGE_PROFILE / name)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spreadsheet-id", required=True)
    parser.add_argument("--gid", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    prepare_profile()
    sheet_url = f"https://docs.google.com/spreadsheets/d/{args.spreadsheet_id}/edit?gid={args.gid}"
    export_url = f"https://docs.google.com/spreadsheets/d/{args.spreadsheet_id}/export?format=xlsx&gid={args.gid}"

    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            str(TEMP_PROFILE),
            executable_path=EDGE_BINARY,
            headless=True,
            args=[f"--profile-directory={EDGE_PROFILE}"],
            ignore_default_args=["--password-store=basic", "--use-mock-keychain"],
        )
        page = context.new_page()
        print("checking_google_session", flush=True)
        page.goto(sheet_url, wait_until="domcontentloaded", timeout=30_000)
        if "accounts.google.com" in page.url:
            raise SystemExit("The copied Edge profile is not signed in to Google for this sheet.")
        print("exporting_selected_tab", flush=True)
        response = page.request.get(export_url, timeout=30_000)
        if not response.ok:
            raise SystemExit(f"Google Sheet export failed with HTTP {response.status}.")
        args.output.write_bytes(response.body())
        context.close()
    print(f"exported_workbook={args.output}")


if __name__ == "__main__":
    main()
