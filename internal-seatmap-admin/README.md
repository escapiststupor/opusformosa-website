# Opus Formosa Internal Seatmap Admin

FastAPI + SQLite MVP for managing internal Friends VIP seat assignments.

This app is intentionally small:

- SQLite stores seat catalog snapshots and internal overrides.
- Admin pages let staff search seats and set internal status / assignee.
- Public API returns seat status without exposing assignee names.
- Existing GitHub Pages static seatmaps can remain as fallback.

## Local Setup

```bash
cd internal-seatmap-admin
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m app.import_existing --repo-root ..
uvicorn app.main:app --reload
```

Then open:

- Admin UI: <http://localhost:8000/admin>
- Public API example: <http://localhost:8000/public-seatmap/2070048441140207616>

## Deployment Shape

Production should run with Google login and a persistent Fly.io volume.

### Google Login

Local development uses `ADMIN_AUTH_MODE=dev`. Production should use:

```bash
ADMIN_AUTH_MODE=google
```

Create a Google OAuth Web application client with this redirect URI:

```text
https://api.opusformosa.org/auth/callback
```

Only emails listed in `ADMIN_ALLOWED_EMAILS` can enter `/admin`.

### Fly.io

Create the app and volume:

```bash
cd internal-seatmap-admin
flyctl launch --name opus-seatmap-admin --region nrt --no-deploy
flyctl volumes create seatmap_data --app opus-seatmap-admin --region nrt --size 1
```

Make sure the generated `fly.toml` contains:

```toml
[env]
  DATABASE_PATH = "/data/seatmap.db"
  ADMIN_AUTH_MODE = "google"
  BASE_URL = "https://api.opusformosa.org"
  CORS_ORIGINS = "https://opusformosa.org,https://www.opusformosa.org"
  PUBLIC_SEATMAP_ALLOWED_ORIGINS = "https://opusformosa.org,https://www.opusformosa.org"
  OPENTIX_ASSETS_DIR = "/data/opentix"

[mounts]
  source = "seatmap_data"
  destination = "/data"

[http_service]
  internal_port = 8000
  force_https = true
  auto_stop_machines = "stop"
  auto_start_machines = true
  min_machines_running = 1
```

Set secrets:

```bash
flyctl secrets set --app opus-seatmap-admin \
  SESSION_SECRET="$(openssl rand -hex 32)" \
  SEATMAP_SYNC_TOKEN="$(openssl rand -hex 32)" \
  ADMIN_ALLOWED_EMAILS="owner@example.com,assistant@example.com" \
  GOOGLE_CLIENT_ID="..." \
  GOOGLE_CLIENT_SECRET="..."
```

Deploy:

```bash
flyctl deploy --app opus-seatmap-admin
```

### Initialize Production SQLite

Do not commit `data/seatmap.db`; it contains internal assignment data.
Instead, generate it locally and upload it to the Fly volume once:

```bash
cd internal-seatmap-admin
DATABASE_PATH=./data/seatmap.db python -m app.import_existing --repo-root .. --reset
flyctl ssh sftp put --app opus-seatmap-admin ./data/seatmap.db /data/seatmap.db
```

After uploading the DB, restart the app:

```bash
flyctl machine restart --app opus-seatmap-admin
```

### GitHub Actions OPENTIX Sync

The GitHub cron still generates the static OPENTIX snapshots in
`assets/opentix/` and `seatmap/opentix/`. It can also update the production
SQLite DB by POSTing each generated `*-seats.json` and `*-seatmap.svg` to:

```text
https://api.opusformosa.org/internal/opentix-sync/events/:eventId
```

Create the same random token in both places:

```bash
TOKEN="$(openssl rand -hex 32)"
flyctl secrets set --app opus-seatmap-admin SEATMAP_SYNC_TOKEN="$TOKEN"
gh secret set SEATMAP_ADMIN_SYNC_TOKEN --body "$TOKEN"
```

The sync endpoint updates only official OPENTIX seat fields and synced SVGs.
It preserves internal `pulled` and `vip_assigned` overrides made by staff in
the admin UI. Generated `public_sold` overrides from the old static import are
removed because public sold status is now derived from the latest OPENTIX
snapshot.

### Public Seatmap API Origin Check

`/public-seatmap/:eventId` returns anonymous availability only; it never returns
assignee names. In production it also checks the browser `Origin` header, with
`Referer` as a fallback, against `PUBLIC_SEATMAP_ALLOWED_ORIGINS`.

This is a browser-origin guard rather than a secret auth mechanism. It prevents
other sites from casually fetching the API from a browser, but a non-browser
client can still spoof headers. Keep sensitive internal fields out of the public
response.

### Custom Domain

For production API URLs, point `api.opusformosa.org` to this Fly app:

```bash
flyctl certs add --app opus-seatmap-admin api.opusformosa.org
flyctl certs show --app opus-seatmap-admin api.opusformosa.org
```

Then add the DNS records requested by Fly and keep `BASE_URL` set to
`https://api.opusformosa.org`.
