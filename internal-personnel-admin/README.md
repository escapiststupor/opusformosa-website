# Opus Formosa Personnel

Internal people directory for musicians and collaborators. This first increment provides a shared Google-login directory with search, editable names, roles, contact data, identity-document status, and payment-account fields.

## Local run

```bash
cp .env.example .env
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --reload
```

Open http://localhost:8000/admin.

## Production

The production app uses the same Google OAuth pattern as the internal seatmap service. Configure `APP_AUTH_MODE=google`, list all internal emails in `APP_ALLOWED_EMAILS`, and set `SESSION_SECRET`, `GOOGLE_CLIENT_ID`, and `GOOGLE_CLIENT_SECRET` as Fly secrets.

The SQLite database is stored at `/data/personnel.db`; identity files are stored privately at `/data/personnel-documents`. Each file is served only through an authenticated admin download route, never a public URL. Before production use, add a daily encrypted backup and periodic restore check. Google Sheets sync, DocuSign, and payment batches are intentionally not included in this first increment.
