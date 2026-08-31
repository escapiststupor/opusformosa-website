"""Authorize opusformosa@gmail.com and update confirmed rehearsal times in Google Sheets."""

import base64
import hashlib
import json
import secrets
import threading
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


SPREADSHEET_ID = "1Equ3xIzzonJlaEIL-GLux4WqBYsWak6V"
SHEET_GID = 280949069
EXPECTED_EMAIL = "opusformosa@gmail.com"
CREDENTIALS_PATH = Path("/Users/pyen/OpusFormosa/telegram_reminder_bot/credentials.json")
TOKEN_PATH = Path("/private/tmp/opus_sheets_edit_token.json")
SCOPES = ["openid", "email", "https://www.googleapis.com/auth/spreadsheets"]


def request_json(url, *, method="GET", token=None, payload=None):
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise SystemExit(f"Google API error {error.code}: {detail}")


def authorize():
    credentials = json.loads(CREDENTIALS_PATH.read_text(encoding="utf-8"))["installed"]
    state = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).rstrip(b"=").decode()
    result = {}

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            result.update({key: values[0] for key, values in urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).items()})
            body = "<meta charset='utf-8'><h2>Authorization received. You may return to Codex.</h2>".encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_args):
            return

    server = HTTPServer(("127.0.0.1", 0), CallbackHandler)
    redirect_uri = f"http://127.0.0.1:{server.server_port}/"
    params = {
        "client_id": credentials["client_id"],
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent select_account",
        "login_hint": EXPECTED_EMAIL,
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    threading.Thread(target=server.handle_request, daemon=True).start()
    webbrowser.open(credentials["auth_uri"] + "?" + urllib.parse.urlencode(params), new=1)
    # Allow enough time for the one-time browser consent; do not continue without it.
    import time
    deadline = time.time() + 600
    while not result and time.time() < deadline:
        time.sleep(0.2)
    server.server_close()
    if not result:
        raise SystemExit("Timed out waiting for Google authorization")
    if result.get("state") != state or "error" in result:
        raise SystemExit("Google authorization was not completed")
    token_request = urllib.request.Request(
        credentials["token_uri"],
        data=urllib.parse.urlencode({
            "client_id": credentials["client_id"],
            "client_secret": credentials["client_secret"],
            "code": result["code"],
            "code_verifier": verifier,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        }).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(token_request, timeout=30) as response:
        token = json.load(response)
    email = request_json(
        "https://www.googleapis.com/oauth2/v2/userinfo", token=token["access_token"]
    ).get("email", "")
    if email.lower() != EXPECTED_EMAIL:
        raise SystemExit("Please authorize opusformosa@gmail.com")
    TOKEN_PATH.write_text(json.dumps(token), encoding="utf-8")
    TOKEN_PATH.chmod(0o600)
    return token["access_token"]


def main():
    token = (
        json.loads(TOKEN_PATH.read_text(encoding="utf-8")).get("access_token")
        if TOKEN_PATH.exists()
        else authorize()
    )
    metadata = request_json(
        f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}?includeGridData=true",
        token=token,
    )
    sheet = next((s for s in metadata["sheets"] if s["properties"]["sheetId"] == SHEET_GID), None)
    if not sheet:
        raise SystemExit("Individual schedules sheet was not found")
    title = sheet["properties"]["title"]
    rows = sheet.get("data", [{}])[0].get("rowData", [])
    updates = []
    current_player = None
    current_date = None
    targets = {
        ("Sep 3", "Shostakovich: Piano Concerto No.1"): "19:15–21:45",
        ("Sep 8", "Dvořák: Piano Quintet Op.81"): "19:00–21:30",
        ("Sep 12", "Dress Rehearsal"): "09:30–12:00",
    }
    for row_number, row in enumerate(rows, start=1):
        values = [cell.get("formattedValue", "") for cell in row.get("values", [])]
        values += [""] * (5 - len(values))
        first, session, time, event, venue = values[:5]
        if first and not any(values[1:5]):
            current_player = first
            current_date = None
            continue
        if first == "Date" and session == "Session":
            current_date = None
            continue
        if first:
            current_date = first
        if not current_player or not current_date or not time or not event:
            continue
        for (target_date, event_fragment), replacement in targets.items():
            if current_date == target_date and event_fragment in event:
                updates.append({"range": f"'{title}'!C{row_number}", "values": [[replacement]]})
                break
    expected_counts = {"19:15–21:45": 5, "19:00–21:30": 5, "09:30–12:00": 9}
    counts = {value: sum(update["values"] == [[value]] for update in updates) for value in expected_counts}
    if counts != expected_counts:
        raise SystemExit(f"Refusing update: expected {expected_counts}, found {counts}")
    response = request_json(
        f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}/values:batchUpdate",
        method="POST",
        token=token,
        payload={"valueInputOption": "USER_ENTERED", "data": updates},
    )
    print(f"updated_cells={response.get('totalUpdatedCells', 0)}")
    print("Sep 3 Shostakovich: 5 rows → 19:15–21:45")
    print("Sep 8 Dvořák: 5 rows → 19:00–21:30")
    print("Sep 12 dress rehearsal: 9 rows → 09:30–12:00")


if __name__ == "__main__":
    main()
