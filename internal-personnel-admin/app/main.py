from __future__ import annotations

import os
import secrets
import smtplib
import urllib.parse
import uuid
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from sqlite3 import Connection
from email.message import EmailMessage
from email.utils import formataddr

from authlib.integrations.starlette_client import OAuth, OAuthError
from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import FileResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from .config import APP_ROOT, allowed_emails, auth_mode, base_url, dev_email, document_storage_path, google_client_id, google_client_secret, mail_from, mail_from_name, smtp_enabled, smtp_host, smtp_password, smtp_port, smtp_username
from .db import get_db, init_db
from .labor_pdf import INCOME_LABELS, render_labor_report_pdf


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="Opus Formosa Personnel", lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=os.environ.get("SESSION_SECRET", "dev-only-change-me"))
app.mount("/static", StaticFiles(directory=APP_ROOT / "app" / "static"), name="static")
templates = Jinja2Templates(directory=APP_ROOT / "app" / "templates")
templates.env.globals["auth_mode"] = auth_mode

ALLOWED_DOCUMENT_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".heic"}
ALLOWED_SIGNED_REPORT_EXTENSIONS = {".pdf"}
MAX_DOCUMENT_BYTES = 20 * 1024 * 1024
LABOR_REPORT_INTERNAL_COPY_EMAIL = "opusformosa@gmail.com"
ID_DOCUMENT_TYPES = ("未設定", "身分證字號", "居留證號碼", "護照號碼")
RESIDENCY_STATUSES = ("未設定", "本國籍", "本國籍但未在台居住", "外國籍在台滿183天", "外國籍在台未達183天")

oauth = OAuth()
oauth.register(
    name="google",
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_id=google_client_id(),
    client_secret=google_client_secret(),
    client_kwargs={"scope": "openid email profile"},
)


def require_staff(request: Request) -> str:
    email = dev_email() if auth_mode() == "dev" else str(request.session.get("staff_email") or request.session.get("admin_email") or "").strip().lower()
    if not email:
        raise HTTPException(status_code=401, detail="請先登入 Google。")
    allowed = allowed_emails()
    if allowed and email not in allowed:
        raise HTTPException(status_code=403, detail="這個 Google 帳戶不在內部名單中。")
    return email


def safe_next(value: str | None) -> str:
    path = str(value or "").strip()
    return path if path.startswith(("/admin", "/personnel")) and not path.startswith("//") else "/admin"


def root_prefix(request: Request) -> str:
    return str(request.scope.get("root_path") or "").rstrip("/")


def admin_base(request: Request) -> str:
    return f"{root_prefix(request)}/admin"


@app.exception_handler(HTTPException)
async def redirect_login(request: Request, exc: HTTPException) -> Response:
    if exc.status_code == 401 and request.url.path.startswith(("/admin", "/personnel/admin")) and "text/html" in request.headers.get("accept", ""):
        return RedirectResponse(f"/auth/login?next={urllib.parse.quote(safe_next(request.url.path), safe='')}", status_code=303)
    return await http_exception_handler(request, exc)


@app.get("/auth/login")
async def login(request: Request, next: str = "/admin") -> Response:
    if auth_mode() == "dev":
        return RedirectResponse(safe_next(next), status_code=303)
    if not google_client_id() or not google_client_secret():
        raise HTTPException(status_code=500, detail="尚未設定 Google OAuth client。")
    request.session["login_next"] = safe_next(next)
    redirect_uri = f"{base_url()}/auth/callback" if base_url() else str(request.url_for("auth_callback"))
    return await oauth.google.authorize_redirect(request, redirect_uri)


@app.get("/auth/callback")
async def auth_callback(request: Request) -> Response:
    try:
        token = await oauth.google.authorize_access_token(request)
    except OAuthError as error:
        raise HTTPException(status_code=401, detail=f"Google 登入失敗：{error.error}") from error
    userinfo = token.get("userinfo") or (await oauth.google.get("userinfo", token=token)).json()
    email = str(userinfo.get("email") or "").strip().lower()
    if not email:
        raise HTTPException(status_code=401, detail="Google 帳戶沒有回傳 Email。")
    allowed = allowed_emails()
    if allowed and email not in allowed:
        raise HTTPException(status_code=403, detail="這個 Google 帳戶不在內部名單中。")
    request.session["staff_email"] = email
    return RedirectResponse(safe_next(str(request.session.pop("login_next", "/admin"))), status_code=303)


@app.post("/auth/logout")
def logout(request: Request) -> Response:
    request.session.clear()
    return RedirectResponse("/admin", status_code=303)


def role_names(db: Connection, person_id: str) -> list[str]:
    return [str(row[0]) for row in db.execute("SELECT role_name FROM person_roles WHERE person_id = ? ORDER BY role_name", (person_id,))]


def person_or_404(db: Connection, person_id: str) -> dict:
    row = db.execute("SELECT * FROM people WHERE id = ?", (person_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="找不到這位人員。")
    person = dict(row)
    person["roles"] = role_names(db, person_id)
    return person


def person_documents(db: Connection, person_id: str) -> list[dict]:
    return [dict(row) for row in db.execute(
        "SELECT * FROM person_documents WHERE person_id = ? ORDER BY created_at DESC, original_filename COLLATE NOCASE",
        (person_id,),
    )]


def document_path(person_id: str, stored_filename: str, storage_path: str = "") -> Path:
    root = document_storage_path().resolve()
    relative_path = Path(storage_path) if storage_path else Path(person_id) / stored_filename
    candidate = (root / relative_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as error:
        raise HTTPException(status_code=404, detail="檔案暫時無法讀取。") from error
    return candidate


def stored_file_path(storage_path: str) -> Path:
    root = document_storage_path().resolve()
    candidate = (root / storage_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as error:
        raise HTTPException(status_code=404, detail="檔案暫時無法讀取。") from error
    return candidate


def has_required_id_material(db: Connection, person_id: str) -> bool:
    row = db.execute(
        """SELECT p.id_document_number, p.id_document_type, p.residency_status, EXISTS(
          SELECT 1 FROM person_documents d WHERE d.person_id = p.id
        ) AS has_file FROM people p WHERE p.id = ?""",
        (person_id,),
    ).fetchone()
    return bool(
        row and str(row["id_document_number"] or "").strip() and row["has_file"]
        and row["id_document_type"] in ID_DOCUMENT_TYPES[1:] and row["residency_status"] in RESIDENCY_STATUSES[1:]
    )


def eligible_people(db: Connection) -> list[dict]:
    return [dict(row) for row in db.execute(
        """SELECT p.*, GROUP_CONCAT(DISTINCT pr.role_name) AS roles
        FROM people p
        LEFT JOIN person_roles pr ON pr.person_id = p.id
        WHERE p.is_active = 1 AND TRIM(COALESCE(p.id_document_number, '')) <> ''
          AND p.id_document_type IN ('身分證字號', '居留證號碼', '護照號碼')
          AND p.residency_status IN ('本國籍', '本國籍但未在台居住', '外國籍在台滿183天', '外國籍在台未達183天')
          AND EXISTS (SELECT 1 FROM person_documents d WHERE d.person_id = p.id)
        GROUP BY p.id ORDER BY p.display_name COLLATE NOCASE"""
    )]


def category_for_person(person: dict) -> str:
    text = f"{person.get('residency_status') or ''} {person.get('nationality') or ''}".lower()
    return "9A_nonresident" if "未達" in text or "未居住" in text or "nonresident" in text else "9A_resident"


def calculate_deductions(category: str, gross_amount: int) -> tuple[float, int, int, int]:
    """Current rules mirror the existing internal payment workbook; money stays integer TWD."""
    if gross_amount < 0:
        raise HTTPException(status_code=400, detail="金額不可為負數。")
    if category in {"9A_nonresident", "9B_nonresident"}:
        rate = 0.20 if gross_amount > 5000 else 0
        health = 0
    elif category == "50_salary":
        rate = 0.05 if gross_amount > 90501 else 0
        health = round(gross_amount * 0.0211) if gross_amount >= 20000 else 0
    else:
        rate = 0.10 if gross_amount > 20000 else 0
        health = round(gross_amount * 0.0211) if gross_amount >= 20000 else 0
    tax = round(gross_amount * rate)
    return rate, tax, health, gross_amount - tax - health


def parse_amount(value: str, field_name: str = "金額") -> int:
    cleaned = str(value or "").strip().replace(",", "")
    if not cleaned or not cleaned.isdigit():
        raise HTTPException(status_code=400, detail=f"{field_name}請填入整數金額。")
    return int(cleaned)


def month_value(value: str) -> str:
    cleaned = str(value or "").strip()
    if len(cleaned) != 7 or cleaned[4] != "-" or not cleaned.replace("-", "").isdigit():
        raise HTTPException(status_code=400, detail="付款月份格式需為 YYYY-MM。")
    return cleaned


def report_or_404(db: Connection, report_id: str) -> dict:
    row = db.execute("SELECT * FROM labor_reports WHERE id = ?", (report_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="找不到這張勞報單。")
    return with_work_period(dict(row))


def with_work_period(report: dict) -> dict:
    start = str(report.get("work_start_date") or report.get("work_date") or "")
    end = str(report.get("work_end_date") or "")
    report["work_period"] = start if not end or end == start else f"{start} 至 {end}"
    return report


def person_labor_reports(db: Connection, person_id: str) -> list[dict]:
    return [with_work_period(dict(row)) for row in db.execute(
        """SELECT lr.*, COUNT(lre.id) AS email_count, MAX(lre.sent_at) AS last_emailed_at
        FROM labor_reports lr LEFT JOIN labor_report_emails lre ON lre.labor_report_id = lr.id
        WHERE lr.person_id = ? GROUP BY lr.id ORDER BY lr.work_date DESC, lr.created_at DESC""", (person_id,)
    )]


@app.get("/")
def home() -> Response:
    return RedirectResponse("admin", status_code=303)


@app.get("/admin")
def people_index(request: Request, db: Connection = Depends(get_db), _: str = Depends(require_staff)):
    people = [dict(row) for row in db.execute(
        f"""
        SELECT p.*, GROUP_CONCAT(DISTINCT pr.role_name) AS roles
        FROM people p LEFT JOIN person_roles pr ON pr.person_id = p.id
        GROUP BY p.id ORDER BY p.display_name COLLATE NOCASE
        """,
    )]
    return templates.TemplateResponse(request, "people.html", {"people": people, "admin_base": admin_base(request), "root_prefix": root_prefix(request)})


@app.get("/admin/people/new")
def new_person(request: Request, _: str = Depends(require_staff)):
    return templates.TemplateResponse(request, "person_form.html", {"person": {}, "roles_text": "", "is_new": True, "id_document_types": ID_DOCUMENT_TYPES, "residency_statuses": RESIDENCY_STATUSES, "admin_base": admin_base(request), "root_prefix": root_prefix(request)})


@app.get("/admin/people/{person_id}")
def edit_person(request: Request, person_id: str, db: Connection = Depends(get_db), _: str = Depends(require_staff)):
    person = person_or_404(db, person_id)
    return templates.TemplateResponse(request, "person_form.html", {
        "person": person,
        "roles_text": "、".join(person["roles"]),
        "documents": person_documents(db, person_id),
        "labor_reports": person_labor_reports(db, person_id),
        "labor_report_eligible": has_required_id_material(db, person_id),
        "income_labels": INCOME_LABELS,
        "id_document_types": ID_DOCUMENT_TYPES,
        "residency_statuses": RESIDENCY_STATUSES,
        "is_new": False,
        "admin_base": admin_base(request),
        "root_prefix": root_prefix(request),
    })


@app.post("/admin/people/save")
def save_person(
    request: Request,
    person_id: str = Form(""),
    display_name: str = Form(...),
    legal_name_zh: str = Form(""), legal_name_en: str = Form(""), email: str = Form(""), phone: str = Form(""), line_id: str = Form(""),
    nationality: str = Form(""), residency_status: str = Form(""), birth_date: str = Form(""), professional_experience: str = Form(""), id_document_type: str = Form(""), id_document_number: str = Form(""),
    id_document_status: str = Form("missing"), id_document_note: str = Form(""), permanent_address: str = Form(""), mailing_address: str = Form(""),
    bank_name: str = Form(""), bank_code: str = Form(""), bank_branch: str = Form(""), bank_branch_code: str = Form(""), bank_account_holder: str = Form(""), bank_account_number: str = Form(""),
    role_names_text: str = Form(""), notes: str = Form(""), is_active: str | None = Form(None),
    db: Connection = Depends(get_db), actor: str = Depends(require_staff),
):
    person_id = person_id or str(uuid.uuid4())
    clean_roles = sorted({part.strip() for part in role_names_text.replace("、", ",").replace("\n", ",").split(",") if part.strip()})
    if id_document_status not in {"missing", "received", "verified"}:
        raise HTTPException(status_code=400, detail="不正確的證件狀態。")
    if id_document_type.strip() and id_document_type.strip() not in ID_DOCUMENT_TYPES:
        raise HTTPException(status_code=400, detail="請從證件類型選單選擇。")
    if residency_status.strip() and residency_status.strip() not in RESIDENCY_STATUSES:
        raise HTTPException(status_code=400, detail="請從居住狀態選單選擇。")
    values = (display_name.strip(), legal_name_zh.strip(), legal_name_en.strip(), email.strip(), phone.strip(), line_id.strip(), nationality.strip(), residency_status.strip(), birth_date.strip(), professional_experience.strip(), id_document_type.strip(), id_document_number.strip(), id_document_status, id_document_note.strip(), permanent_address.strip(), mailing_address.strip(), bank_name.strip(), bank_code.strip(), bank_branch.strip(), bank_branch_code.strip(), bank_account_holder.strip(), bank_account_number.strip(), notes.strip(), 1 if is_active else 0)
    exists = db.execute("SELECT 1 FROM people WHERE id = ?", (person_id,)).fetchone()
    if exists:
        db.execute("""UPDATE people SET display_name=?, legal_name_zh=?, legal_name_en=?, email=?, phone=?, line_id=?, nationality=?, residency_status=?, birth_date=?, professional_experience=?, id_document_type=?, id_document_number=?, id_document_status=?, id_document_note=?, permanent_address=?, mailing_address=?, bank_name=?, bank_code=?, bank_branch=?, bank_branch_code=?, bank_account_holder=?, bank_account_number=?, notes=?, is_active=?, updated_at=CURRENT_TIMESTAMP WHERE id=?""", (*values, person_id))
        action = "updated"
    else:
        db.execute("""INSERT INTO people (id, display_name, legal_name_zh, legal_name_en, email, phone, line_id, nationality, residency_status, birth_date, professional_experience, id_document_type, id_document_number, id_document_status, id_document_note, permanent_address, mailing_address, bank_name, bank_code, bank_branch, bank_branch_code, bank_account_holder, bank_account_number, notes, is_active) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (person_id, *values))
        action = "created"
    db.execute("DELETE FROM person_roles WHERE person_id = ?", (person_id,))
    db.executemany("INSERT INTO person_roles (person_id, role_name) VALUES (?, ?)", [(person_id, name) for name in clean_roles])
    db.execute("INSERT INTO audit_log (person_id, action, actor_email) VALUES (?, ?, ?)", (person_id, action, actor))
    db.commit()
    return RedirectResponse(f"{admin_base(request)}/people/{person_id}?saved=1", status_code=303)


@app.post("/admin/people/{person_id}/documents")
async def upload_person_documents(
    request: Request,
    person_id: str,
    files: list[UploadFile] = File(...),
    db: Connection = Depends(get_db),
    actor: str = Depends(require_staff),
):
    person_or_404(db, person_id)
    stored_count = 0
    target_dir = document_storage_path() / person_id
    target_dir.mkdir(parents=True, exist_ok=True)
    saved_paths: list[Path] = []
    for upload in files:
        original_filename = Path(upload.filename or "").name
        extension = Path(original_filename).suffix.lower()
        if not original_filename or extension not in ALLOWED_DOCUMENT_EXTENSIONS:
            raise HTTPException(status_code=400, detail="只接受 PDF、PNG、JPG、JPEG 或 HEIC 證件檔。")
    try:
        for upload in files:
            original_filename = Path(upload.filename or "").name
            extension = Path(original_filename).suffix.lower()
            contents = await upload.read(MAX_DOCUMENT_BYTES + 1)
            if not contents:
                raise HTTPException(status_code=400, detail="無法上傳空白檔案。")
            if len(contents) > MAX_DOCUMENT_BYTES:
                raise HTTPException(status_code=400, detail="單一檔案不可超過 20 MB。")
            document_id = str(uuid.uuid4())
            stored_filename = f"{document_id}{extension}"
            target = document_path(person_id, stored_filename)
            target.write_bytes(contents)
            target.chmod(0o600)
            saved_paths.append(target)
            db.execute(
            """INSERT INTO person_documents
               (id, person_id, original_filename, stored_filename, storage_path, content_type, file_size, uploaded_by)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (document_id, person_id, original_filename, stored_filename, f"{person_id}/{stored_filename}", upload.content_type or "", str(len(contents)), actor),
            )
            stored_count += 1
    except Exception:
        db.rollback()
        for path in saved_paths:
            path.unlink(missing_ok=True)
        raise
    if stored_count:
        db.execute(
            """UPDATE people SET id_document_status = 'received',
               id_document_note = CASE WHEN id_document_note = '' THEN '已收到證件檔，待核驗' ELSE id_document_note END,
               updated_at = CURRENT_TIMESTAMP WHERE id = ?""",
            (person_id,),
        )
        db.execute("INSERT INTO audit_log (person_id, action, actor_email) VALUES (?, ?, ?)", (person_id, f"uploaded_document:{stored_count}", actor))
        db.commit()
    return RedirectResponse(f"{admin_base(request)}/people/{person_id}?uploaded={stored_count}", status_code=303)


@app.get("/admin/people/{person_id}/documents/{document_id}/download")
def download_person_document(
    person_id: str,
    document_id: str,
    db: Connection = Depends(get_db),
    _: str = Depends(require_staff),
):
    document = db.execute(
        "SELECT * FROM person_documents WHERE id = ? AND person_id = ?",
        (document_id, person_id),
    ).fetchone()
    if not document:
        raise HTTPException(status_code=404, detail="找不到這份證件檔。")
    path = document_path(person_id, str(document["stored_filename"]), str(document["storage_path"] or ""))
    if not path.is_file():
        raise HTTPException(status_code=404, detail="檔案暫時無法讀取。")
    return FileResponse(path, media_type=str(document["content_type"] or "application/octet-stream"), filename=str(document["original_filename"]))


@app.get("/admin/people/{person_id}/documents/{document_id}/preview")
def preview_person_document(
    person_id: str,
    document_id: str,
    db: Connection = Depends(get_db),
    _: str = Depends(require_staff),
):
    document = db.execute(
        "SELECT * FROM person_documents WHERE id = ? AND person_id = ?",
        (document_id, person_id),
    ).fetchone()
    if not document:
        raise HTTPException(status_code=404, detail="找不到這份證件檔。")
    path = document_path(person_id, str(document["stored_filename"]), str(document["storage_path"] or ""))
    if not path.is_file():
        raise HTTPException(status_code=404, detail="檔案暫時無法讀取。")
    return FileResponse(
        path,
        media_type=str(document["content_type"] or "application/octet-stream"),
        filename=Path(str(document["original_filename"])).name,
        content_disposition_type="inline",
    )


@app.get("/admin/labor-reports/new")
def new_batch_labor_reports(request: Request, db: Connection = Depends(get_db), _: str = Depends(require_staff)):
    return templates.TemplateResponse(request, "labor_report_form.html", {
        "people": eligible_people(db),
        "single_person": None,
        "income_labels": INCOME_LABELS,
        "default_month": date.today().strftime("%Y-%m"),
        "default_issue_date": date.today().isoformat(),
        "admin_base": admin_base(request),
        "root_prefix": root_prefix(request),
    })


@app.get("/admin/people/{person_id}/labor-reports/new")
def new_person_labor_report(request: Request, person_id: str, db: Connection = Depends(get_db), _: str = Depends(require_staff)):
    person = person_or_404(db, person_id)
    if not has_required_id_material(db, person_id):
        raise HTTPException(status_code=400, detail="此人缺少證件號碼或已上傳的證件檔，不能建立勞報單。")
    return templates.TemplateResponse(request, "labor_report_form.html", {
        "people": [person],
        "single_person": person,
        "income_labels": INCOME_LABELS,
        "default_category": category_for_person(person),
        "default_month": date.today().strftime("%Y-%m"),
        "default_issue_date": date.today().isoformat(),
        "admin_base": admin_base(request),
        "root_prefix": root_prefix(request),
    })


@app.post("/admin/labor-reports/create")
async def create_labor_reports(request: Request, db: Connection = Depends(get_db), actor: str = Depends(require_staff)):
    form = await request.form()
    person_ids = list(dict.fromkeys(str(value) for value in form.getlist("person_id") if str(value).strip()))
    if not person_ids:
        raise HTTPException(status_code=400, detail="請至少選擇一位人員。")
    work_start_date = str(form.get("work_start_date") or "").strip()
    work_end_date = str(form.get("work_end_date") or "").strip()
    issue_date = str(form.get("issue_date") or "").strip()
    description = str(form.get("work_description") or "").strip()
    payment_month = month_value(str(form.get("payment_month") or ""))
    payment_method = str(form.get("payment_method") or "wire")
    if payment_method not in {"wire", "cash"}:
        raise HTTPException(status_code=400, detail="不正確的付款方式。")
    if not work_start_date or not issue_date or not description:
        raise HTTPException(status_code=400, detail="請填寫工作開始日期、開立日期與工作項目。")
    if work_end_date and work_end_date < work_start_date:
        raise HTTPException(status_code=400, detail="工作結束日期不可早於開始日期。")

    created: list[str] = []
    written_files: list[Path] = []
    try:
        for person_id in person_ids:
            person = person_or_404(db, person_id)
            if not has_required_id_material(db, person_id):
                raise HTTPException(status_code=400, detail=f"{person['display_name']} 缺少證件號碼或證件檔，不能建立勞報單。")
            category = str(form.get(f"income_category_{person_id}") or category_for_person(person))
            if category not in INCOME_LABELS:
                raise HTTPException(status_code=400, detail="不正確的所得類別。")
            gross_amount = parse_amount(str(form.get(f"gross_amount_{person_id}") or ""), f"{person['display_name']} 的金額")
            rate, tax, health, net = calculate_deductions(category, gross_amount)
            report_id = str(uuid.uuid4())
            storage_path = f"labor_reports/{report_id}/unsigned.pdf"
            report = {
                "id": report_id,
                "recipient_name": str(person.get("legal_name_zh") or person.get("legal_name_en") or person["display_name"]),
                "id_document_type": str(person.get("id_document_type") or "證件號碼"),
                "id_document_number": str(person["id_document_number"]),
                "work_date": work_start_date,
                "work_start_date": work_start_date,
                "work_end_date": work_end_date,
                "work_period": work_start_date if not work_end_date or work_end_date == work_start_date else f"{work_start_date} 至 {work_end_date}",
                "work_description": description,
                "issue_date": issue_date,
                "payment_month": payment_month,
                "income_category": category,
                "payment_method": payment_method,
                "gross_amount": gross_amount,
                "withholding_rate": rate,
                "withholding_tax": tax,
                "supplemental_health_insurance": health,
                "net_amount": net,
                "bank_name": str(person.get("bank_name") or ""),
                "bank_code": str(person.get("bank_code") or ""),
                "bank_branch": str(person.get("bank_branch") or ""),
                "bank_branch_code": str(person.get("bank_branch_code") or ""),
                "bank_account_holder": str(person.get("bank_account_holder") or ""),
                "bank_account_number": str(person.get("bank_account_number") or ""),
                "unsigned_storage_path": storage_path,
            }
            output = stored_file_path(storage_path)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(render_labor_report_pdf(report, person))
            output.chmod(0o600)
            written_files.append(output)
            db.execute(
                """INSERT INTO labor_reports
                (id, person_id, recipient_name, id_document_type, id_document_number, work_date, work_start_date, work_end_date, work_description, issue_date,
                 payment_month, income_category, payment_method, gross_amount, withholding_rate, withholding_tax,
                 supplemental_health_insurance, net_amount, bank_name, bank_code, bank_branch, bank_branch_code,
                 bank_account_holder, bank_account_number, unsigned_storage_path, created_by)
                VALUES (:id, :person_id, :recipient_name, :id_document_type, :id_document_number, :work_date, :work_start_date, :work_end_date,
                 :work_description, :issue_date, :payment_month, :income_category, :payment_method, :gross_amount,
                 :withholding_rate, :withholding_tax, :supplemental_health_insurance, :net_amount, :bank_name,
                 :bank_code, :bank_branch, :bank_branch_code, :bank_account_holder, :bank_account_number,
                 :unsigned_storage_path, :created_by)""",
                {**report, "person_id": person_id, "created_by": actor},
            )
            db.execute("INSERT INTO audit_log (person_id, action, actor_email) VALUES (?, ?, ?)", (person_id, f"created_labor_report:{report_id}", actor))
            created.append(report_id)
        db.commit()
    except Exception:
        db.rollback()
        for output in written_files:
            output.unlink(missing_ok=True)
        raise
    if len(created) == 1:
        return RedirectResponse(f"{admin_base(request)}/people/{person_ids[0]}?labor_report_created=1", status_code=303)
    return RedirectResponse(f"{admin_base(request)}/payments?month={payment_month}&created={len(created)}", status_code=303)


@app.get("/admin/labor-reports/{report_id}/unsigned")
def preview_unsigned_labor_report(report_id: str, db: Connection = Depends(get_db), _: str = Depends(require_staff)):
    report = report_or_404(db, report_id)
    path = stored_file_path(str(report["unsigned_storage_path"]))
    if not path.is_file():
        raise HTTPException(status_code=404, detail="未簽版 PDF 暫時無法讀取。")
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=f"{report['recipient_name']}_{report['work_date']}_勞務報酬單_未簽.pdf",
        content_disposition_type="inline",
    )


@app.post("/admin/labor-reports/{report_id}/delete")
def delete_unsigned_labor_report(_: Request, report_id: str, db: Connection = Depends(get_db), __: str = Depends(require_staff)):
    report_or_404(db, report_id)
    raise HTTPException(status_code=410, detail="勞報單不可直接刪除，請改用作廢流程。")


def labor_report_email_defaults(report: dict, person: dict) -> tuple[str, str]:
    name = str(report["recipient_name"] or person["display_name"])
    subject = "[勞報單] 請協助簽署｜福爾摩沙藝響"
    body = f"""{name} 您好：

附件是 {report.get('work_period') or report['work_date']}「{report['work_description']}」的勞務報酬單，敬請確認資料後簽名。

請在 PDF 檔案簽名，並直接回覆此 email 附上已簽檔案。完成回簽後，我們會將這筆款項安排於 {report['payment_month']} 月底付款。

如資料有需要更正之處，也請直接回信告知，謝謝。

福爾摩沙藝響
"""
    return subject, body


def labor_report_void_email_defaults(report: dict, person: dict) -> tuple[str, str]:
    name = str(report["recipient_name"] or person["display_name"])
    subject = "[勞報單作廢] 福爾摩沙藝響"
    body = f"""{name} 您好：

先前寄送的 {report.get('work_period') or report['work_date']}「{report['work_description']}」勞務報酬單，因資料需要更正，現已作廢，請勿簽署或使用該份文件。

如需重新開立，我們會另行寄送新版勞務報酬單。

如有任何問題，請直接回信告知，謝謝。

福爾摩沙藝響
"""
    return subject, body


@app.get("/admin/labor-reports/{report_id}/email")
def compose_labor_report_email(request: Request, report_id: str, db: Connection = Depends(get_db), _: str = Depends(require_staff)):
    report = report_or_404(db, report_id)
    if report["voided_at"]:
        raise HTTPException(status_code=400, detail="這張勞報單已作廢，不能再寄送。")
    person = person_or_404(db, str(report["person_id"]))
    subject, body = labor_report_email_defaults(report, person)
    return templates.TemplateResponse(request, "labor_report_email_form.html", {
        "report": report,
        "person": person,
        "default_subject": subject,
        "default_body": body,
        "smtp_enabled": smtp_enabled(),
        "mail_from": mail_from(),
        "admin_base": admin_base(request),
        "root_prefix": root_prefix(request),
    })


@app.post("/admin/labor-reports/{report_id}/email")
def send_labor_report_email(
    request: Request,
    report_id: str,
    recipient_email: str = Form(...), subject: str = Form(...), body: str = Form(...),
    db: Connection = Depends(get_db), actor: str = Depends(require_staff),
):
    if not smtp_enabled():
        raise HTTPException(status_code=503, detail="尚未設定寄信服務。請先設定 SMTP_USERNAME、SMTP_PASSWORD 與 SMTP_FROM_EMAIL。")
    report = report_or_404(db, report_id)
    if report["voided_at"]:
        raise HTTPException(status_code=400, detail="這張勞報單已作廢，不能再寄送。")
    clean_recipient = recipient_email.strip()
    clean_subject = subject.strip()
    clean_body = body.strip()
    if "@" not in clean_recipient or not clean_subject or not clean_body:
        raise HTTPException(status_code=400, detail="請填寫有效收件人、主旨與內文。")
    attachment = stored_file_path(str(report["unsigned_storage_path"]))
    if not attachment.is_file():
        raise HTTPException(status_code=404, detail="未簽版 PDF 暫時無法讀取，不能寄送。")
    message = EmailMessage()
    message["From"] = formataddr((mail_from_name(), mail_from()))
    message["To"] = clean_recipient
    message["Cc"] = LABOR_REPORT_INTERNAL_COPY_EMAIL
    message["Subject"] = clean_subject
    message.set_content(clean_body)
    filename = f"{report['recipient_name']}_{report['work_date']}_勞務報酬單.pdf"
    message.add_attachment(attachment.read_bytes(), maintype="application", subtype="pdf", filename=filename)
    try:
        if smtp_port() == 465:
            with smtplib.SMTP_SSL(smtp_host(), smtp_port(), timeout=20) as client:
                client.login(smtp_username(), smtp_password())
                client.send_message(message)
        else:
            with smtplib.SMTP(smtp_host(), smtp_port(), timeout=20) as client:
                client.starttls()
                client.login(smtp_username(), smtp_password())
                client.send_message(message)
    except (OSError, smtplib.SMTPException) as error:
        raise HTTPException(status_code=502, detail="寄信服務暫時無法使用，勞報單尚未寄出。請稍後再試。") from error
    email_id = str(uuid.uuid4())
    db.execute(
        "INSERT INTO labor_report_emails (id, labor_report_id, recipient_email, subject, body, sent_by) VALUES (?, ?, ?, ?, ?, ?)",
        (email_id, report_id, clean_recipient, clean_subject, clean_body, actor),
    )
    db.execute("INSERT INTO audit_log (person_id, action, actor_email) VALUES (?, ?, ?)", (report["person_id"], f"sent_labor_report_email:{report_id}", actor))
    db.commit()
    return RedirectResponse(f"{admin_base(request)}/people/{report['person_id']}?labor_report_emailed=1", status_code=303)


@app.get("/admin/labor-reports/{report_id}/void")
def compose_labor_report_void_email(request: Request, report_id: str, db: Connection = Depends(get_db), _: str = Depends(require_staff)):
    report = report_or_404(db, report_id)
    if report["signed_storage_path"]:
        raise HTTPException(status_code=400, detail="已簽版勞報單請先確認付款處理，不能直接作廢。")
    if report["voided_at"]:
        raise HTTPException(status_code=400, detail="這張勞報單已作廢。")
    email_count = db.execute("SELECT COUNT(*) FROM labor_report_emails WHERE labor_report_id = ?", (report_id,)).fetchone()[0]
    if not email_count:
        raise HTTPException(status_code=400, detail="這張勞報單尚未寄送，請直接作廢，不需通知收件人。")
    person = person_or_404(db, str(report["person_id"]))
    latest_email = db.execute(
        "SELECT recipient_email FROM labor_report_emails WHERE labor_report_id = ? ORDER BY sent_at DESC LIMIT 1", (report_id,)
    ).fetchone()
    subject, body = labor_report_void_email_defaults(report, person)
    return templates.TemplateResponse(request, "labor_report_void_form.html", {
        "report": report,
        "person": person,
        "default_recipient": str(latest_email["recipient_email"]) if latest_email else str(person.get("email") or ""),
        "default_subject": subject,
        "default_body": body,
        "smtp_enabled": smtp_enabled(),
        "mail_from": mail_from(),
        "admin_base": admin_base(request),
        "root_prefix": root_prefix(request),
    })


@app.post("/admin/labor-reports/{report_id}/void")
def void_labor_report(
    request: Request,
    report_id: str,
    recipient_email: str = Form(...), subject: str = Form(...), body: str = Form(...),
    db: Connection = Depends(get_db), actor: str = Depends(require_staff),
):
    if not smtp_enabled():
        raise HTTPException(status_code=503, detail="尚未設定寄信服務，因此不能執行作廢通知。")
    report = report_or_404(db, report_id)
    if report["signed_storage_path"] or report["voided_at"]:
        raise HTTPException(status_code=400, detail="這張勞報單目前不能作廢。")
    if not db.execute("SELECT COUNT(*) FROM labor_report_emails WHERE labor_report_id = ?", (report_id,)).fetchone()[0]:
        raise HTTPException(status_code=400, detail="這張勞報單尚未寄送，請直接作廢，不需通知收件人。")
    clean_recipient, clean_subject, clean_body = recipient_email.strip(), subject.strip(), body.strip()
    if "@" not in clean_recipient or not clean_subject or not clean_body:
        raise HTTPException(status_code=400, detail="請填寫有效收件人、主旨與內文。")
    message = EmailMessage()
    message["From"] = formataddr((mail_from_name(), mail_from()))
    message["To"] = clean_recipient
    message["Cc"] = LABOR_REPORT_INTERNAL_COPY_EMAIL
    message["Subject"] = clean_subject
    message.set_content(clean_body)
    try:
        if smtp_port() == 465:
            with smtplib.SMTP_SSL(smtp_host(), smtp_port(), timeout=20) as client:
                client.login(smtp_username(), smtp_password())
                client.send_message(message)
        else:
            with smtplib.SMTP(smtp_host(), smtp_port(), timeout=20) as client:
                client.starttls()
                client.login(smtp_username(), smtp_password())
                client.send_message(message)
    except (OSError, smtplib.SMTPException) as error:
        raise HTTPException(status_code=502, detail="寄信服務暫時無法使用，勞報單尚未作廢。請稍後再試。") from error
    db.execute(
        "UPDATE labor_reports SET voided_at = CURRENT_TIMESTAMP, voided_by = ? WHERE id = ?", (actor, report_id)
    )
    db.execute(
        "INSERT INTO labor_report_emails (id, labor_report_id, recipient_email, subject, body, sent_by) VALUES (?, ?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), report_id, clean_recipient, clean_subject, clean_body, actor),
    )
    db.execute("INSERT INTO audit_log (person_id, action, actor_email) VALUES (?, ?, ?)", (report["person_id"], f"voided_labor_report:{report_id}", actor))
    db.commit()
    return RedirectResponse(f"{admin_base(request)}/people/{report['person_id']}?labor_report_voided=1", status_code=303)


@app.post("/admin/labor-reports/{report_id}/void-without-email")
def void_unemailed_labor_report(
    request: Request,
    report_id: str,
    db: Connection = Depends(get_db), actor: str = Depends(require_staff),
):
    report = report_or_404(db, report_id)
    if report["signed_storage_path"] or report["voided_at"]:
        raise HTTPException(status_code=400, detail="這張勞報單目前不能作廢。")
    if db.execute("SELECT COUNT(*) FROM labor_report_emails WHERE labor_report_id = ?", (report_id,)).fetchone()[0]:
        raise HTTPException(status_code=400, detail="這張勞報單已寄送，請先寄出作廢通知。")
    db.execute("UPDATE labor_reports SET voided_at = CURRENT_TIMESTAMP, voided_by = ? WHERE id = ?", (actor, report_id))
    db.execute("INSERT INTO audit_log (person_id, action, actor_email) VALUES (?, ?, ?)", (report["person_id"], f"voided_unemailed_labor_report:{report_id}", actor))
    db.commit()
    return RedirectResponse(f"{admin_base(request)}/people/{report['person_id']}?labor_report_voided=1", status_code=303)


@app.get("/admin/labor-reports/{report_id}/signed")
def download_signed_labor_report(report_id: str, db: Connection = Depends(get_db), _: str = Depends(require_staff)):
    report = report_or_404(db, report_id)
    if not report["signed_storage_path"]:
        raise HTTPException(status_code=404, detail="尚未上傳已簽版。")
    path = stored_file_path(str(report["signed_storage_path"]))
    if not path.is_file():
        raise HTTPException(status_code=404, detail="已簽版 PDF 暫時無法讀取。")
    return FileResponse(path, media_type="application/pdf", filename=str(report["signed_original_filename"] or f"{report['recipient_name']}_勞務報酬單_已簽.pdf"))


@app.post("/admin/labor-reports/{report_id}/signed")
async def upload_signed_labor_report(
    request: Request,
    report_id: str,
    signed_file: UploadFile = File(...),
    db: Connection = Depends(get_db),
    actor: str = Depends(require_staff),
):
    report = report_or_404(db, report_id)
    if report["voided_at"]:
        raise HTTPException(status_code=400, detail="這張勞報單已作廢，不能上傳已簽版。")
    original_filename = Path(signed_file.filename or "").name
    if not original_filename or Path(original_filename).suffix.lower() not in ALLOWED_SIGNED_REPORT_EXTENSIONS:
        raise HTTPException(status_code=400, detail="已簽版請上傳 PDF。")
    contents = await signed_file.read(MAX_DOCUMENT_BYTES + 1)
    if not contents or len(contents) > MAX_DOCUMENT_BYTES:
        raise HTTPException(status_code=400, detail="已簽版檔案不可為空白且不可超過 20 MB。")
    storage_path = f"labor_reports/{report_id}/signed.pdf"
    target = stored_file_path(storage_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".pdf.uploading")
    temporary.write_bytes(contents)
    temporary.chmod(0o600)
    temporary.replace(target)
    db.execute(
        """UPDATE labor_reports SET signed_storage_path = ?, signed_original_filename = ?,
        signed_uploaded_by = ?, signed_at = CURRENT_TIMESTAMP WHERE id = ?""",
        (storage_path, original_filename, actor, report_id),
    )
    db.execute("INSERT INTO audit_log (person_id, action, actor_email) VALUES (?, ?, ?)", (report["person_id"], f"uploaded_signed_labor_report:{report_id}", actor))
    db.commit()
    return RedirectResponse(f"{admin_base(request)}/people/{report['person_id']}?signed_labor_report=1", status_code=303)


@app.get("/admin/reimbursements/new")
def new_reimbursement(request: Request, month: str = "", db: Connection = Depends(get_db), _: str = Depends(require_staff)):
    return templates.TemplateResponse(request, "reimbursement_form.html", {
        "people": eligible_people(db),
        "payment_month": month if month else date.today().strftime("%Y-%m"),
        "admin_base": admin_base(request),
        "root_prefix": root_prefix(request),
    })


@app.post("/admin/reimbursements/create")
def create_reimbursement(
    request: Request,
    person_id: str = Form(...), payment_month: str = Form(...), amount: str = Form(...), notes: str = Form(""),
    db: Connection = Depends(get_db), actor: str = Depends(require_staff),
):
    person = person_or_404(db, person_id)
    if not has_required_id_material(db, person_id):
        raise HTTPException(status_code=400, detail="此人缺少證件號碼或已上傳的證件檔，不能新增核銷單。")
    clean_month = month_value(payment_month)
    reimbursement_id = str(uuid.uuid4())
    db.execute("INSERT INTO reimbursements (id, person_id, payment_month, amount, notes, created_by) VALUES (?, ?, ?, ?, ?, ?)", (reimbursement_id, person_id, clean_month, parse_amount(amount, "核銷總額"), notes.strip(), actor))
    db.execute("INSERT INTO audit_log (person_id, action, actor_email) VALUES (?, ?, ?)", (person_id, f"created_reimbursement:{reimbursement_id}", actor))
    db.commit()
    return RedirectResponse(f"{admin_base(request)}/payments?month={clean_month}&reimbursement_created=1", status_code=303)


@app.get("/admin/payments")
def payment_overview(request: Request, month: str = "", payment_date: str = "", db: Connection = Depends(get_db), _: str = Depends(require_staff)):
    selected_month = month if month else date.today().strftime("%Y-%m")
    selected_month = month_value(selected_month)
    report_rows = [dict(row) for row in db.execute(
        """SELECT person_id, recipient_name, id_document_number, income_category, payment_method,
           SUM(gross_amount) AS gross_amount, SUM(withholding_tax) AS withholding_tax,
           SUM(supplemental_health_insurance) AS supplemental_health_insurance, SUM(net_amount) AS net_amount,
           GROUP_CONCAT(id) AS report_ids, COUNT(*) AS report_count
        FROM labor_reports
        WHERE payment_month = ? AND signed_storage_path IS NOT NULL AND voided_at IS NULL
        GROUP BY person_id, recipient_name, id_document_number, income_category, payment_method
        ORDER BY recipient_name COLLATE NOCASE, income_category""",
        (selected_month,),
    )]
    reimbursements = [dict(row) for row in db.execute(
        """SELECT r.person_id, SUM(r.amount) AS amount, GROUP_CONCAT(COALESCE(r.notes, ''), '；') AS notes
        FROM reimbursements r WHERE r.payment_month = ? GROUP BY r.person_id""",
        (selected_month,),
    )]
    reimbursement_by_person = {row["person_id"]: row for row in reimbursements}
    seen_people: set[str] = set()
    for row in report_rows:
        reimbursement = reimbursement_by_person.get(row["person_id"], {}) if row["person_id"] not in seen_people else {}
        row["reimbursement_amount"] = int(reimbursement.get("amount") or 0)
        row["reimbursement_notes"] = reimbursement.get("notes") or ""
        row["transfer_total"] = int(row["net_amount"] or 0) + row["reimbursement_amount"]
        row["income_label"] = INCOME_LABELS.get(row["income_category"], row["income_category"])
        row["report_ids"] = str(row["report_ids"]).split(",") if row["report_ids"] else []
        seen_people.add(row["person_id"])
    no_labor_reimbursements = [row for person_id, row in reimbursement_by_person.items() if person_id not in seen_people]
    for row in no_labor_reimbursements:
        person = person_or_404(db, row["person_id"])
        report_rows.append({
            "person_id": row["person_id"], "recipient_name": person.get("legal_name_zh") or person["display_name"],
            "id_document_number": person.get("id_document_number") or "", "income_category": "", "income_label": "—",
            "payment_method": "wire", "gross_amount": 0, "withholding_tax": 0, "supplemental_health_insurance": 0,
            "net_amount": 0, "report_ids": [], "report_count": 0, "reimbursement_amount": int(row["amount"] or 0),
            "reimbursement_notes": row.get("notes") or "", "transfer_total": int(row["amount"] or 0),
        })
    pending_count = db.execute("SELECT COUNT(*) FROM labor_reports WHERE payment_month = ? AND signed_storage_path IS NULL AND voided_at IS NULL", (selected_month,)).fetchone()[0]
    totals = {
        "gross_amount": sum(int(row["gross_amount"] or 0) for row in report_rows),
        "withholding_tax": sum(int(row["withholding_tax"] or 0) for row in report_rows),
        "supplemental_health_insurance": sum(int(row["supplemental_health_insurance"] or 0) for row in report_rows),
        "net_amount": sum(int(row["net_amount"] or 0) for row in report_rows),
        "reimbursement_amount": sum(int(row["reimbursement_amount"] or 0) for row in report_rows),
        "transfer_total": sum(int(row["transfer_total"] or 0) for row in report_rows),
    }
    return templates.TemplateResponse(request, "payment_overview.html", {
        "rows": report_rows,
        "totals": totals,
        "selected_month": selected_month,
        "payment_date": payment_date,
        "pending_count": pending_count,
        "income_labels": INCOME_LABELS,
        "admin_base": admin_base(request),
        "root_prefix": root_prefix(request),
    })
