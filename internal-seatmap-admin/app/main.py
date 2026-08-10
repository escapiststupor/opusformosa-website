from __future__ import annotations

import json
import os
import urllib.parse
from contextlib import asynccontextmanager
from sqlite3 import Connection
from typing import Any

from authlib.integrations.starlette_client import OAuth, OAuthError
from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from .config import (
    APP_ROOT,
    allowed_admin_emails,
    auth_mode,
    base_url,
    cors_origins,
    dev_admin_email,
    google_client_id,
    google_client_secret,
)
from .db import get_db, init_db, row_to_dict, rows_to_dicts


STATUS_LABELS = {
    "vip_available": "VIP 可安排",
    "vip_assigned": "已調票且指定",
    "taken": "已預訂（舊）",
    "pulled": "已調票未指定",
    "public_sold": "已在OPENTIX售出",
    "closed": "不開放",
    "public_available": "公開可售",
}
PUBLIC_STATUS_LABELS = {
    "vip_available": "VIP 可安排",
    "vip_assigned": "已預訂",
    "taken": "已預訂",
    "pulled": "VIP 可安排",
    "public_sold": "已售出",
    "closed": "不開放",
    "public_available": "公開可售",
}

EDITABLE_STATUS_VALUES = ("pulled", "vip_assigned")
ADMIN_STATUS_VALUES = ("pulled", "vip_assigned", "taken")
REPO_ROOT = APP_ROOT.parent
SYSTEM_CLOSED_SECTION_PATTERNS = ("保留", "評鑑席", "館方工作席")


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="Opus Formosa Seatmap Admin", lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=os.environ.get("SESSION_SECRET", "dev-only-change-me"))
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins(),
    allow_credentials=False,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=APP_ROOT / "app" / "static"), name="static")

templates = Jinja2Templates(directory=APP_ROOT / "app" / "templates")
templates.env.filters["status_label"] = lambda value: STATUS_LABELS.get(value, value or "未標記")
templates.env.globals["auth_mode"] = auth_mode

oauth = OAuth()
oauth.register(
    name="google",
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_id=google_client_id(),
    client_secret=google_client_secret(),
    client_kwargs={"scope": "openid email profile"},
)


def require_admin(request: Request) -> str:
    if auth_mode() == "dev":
        email = request.headers.get("x-admin-email", dev_admin_email()).strip().lower()
    else:
        email = str(request.session.get("admin_email") or "").strip().lower()
        if not email:
            raise HTTPException(status_code=401, detail="請先登入 Google。")

    allowed = allowed_admin_emails()
    if allowed and email not in allowed:
        raise HTTPException(status_code=403, detail="這個 Google 帳戶不在允許名單內。")
    return email


def safe_next_url(value: str | None) -> str:
    text = str(value or "").strip()
    if not text.startswith("/admin"):
        return "/admin"
    if text.startswith("//"):
        return "/admin"
    return text


def auth_callback_url(request: Request) -> str:
    configured_base_url = base_url()
    if configured_base_url:
        return f"{configured_base_url}/auth/callback"
    return str(request.url_for("auth_callback"))


async def google_userinfo(request: Request) -> dict[str, Any]:
    if not google_client_id() or not google_client_secret():
        raise HTTPException(status_code=500, detail="尚未設定 Google OAuth client。")
    try:
        token = await oauth.google.authorize_access_token(request)
    except OAuthError as error:
        raise HTTPException(status_code=401, detail=f"Google 登入失敗：{error.error}") from error

    userinfo = token.get("userinfo")
    if userinfo:
        return dict(userinfo)

    response = await oauth.google.get("userinfo", token=token)
    return dict(response.json())


@app.exception_handler(HTTPException)
async def html_auth_exception_handler(request: Request, exc: HTTPException) -> Response:
    accepts_html = "text/html" in request.headers.get("accept", "")
    if exc.status_code == 401 and auth_mode() == "google" and request.url.path.startswith("/admin") and accepts_html:
        path = request.url.path
        if request.url.query:
            path = f"{path}?{request.url.query}"
        encoded_next = urllib.parse.quote(safe_next_url(path), safe="")
        return RedirectResponse(f"/auth/login?next={encoded_next}", status_code=303)
    return await http_exception_handler(request, exc)


@app.get("/auth/login")
async def auth_login(request: Request, next: str = "/admin") -> Response:
    if auth_mode() == "dev":
        return RedirectResponse(safe_next_url(next), status_code=303)
    request.session["login_next"] = safe_next_url(next)
    return await oauth.google.authorize_redirect(request, auth_callback_url(request))


@app.get("/auth/callback")
async def auth_callback(request: Request) -> RedirectResponse:
    userinfo = await google_userinfo(request)
    email = str(userinfo.get("email") or "").strip().lower()
    if not email:
        raise HTTPException(status_code=401, detail="Google 帳戶沒有回傳 Email。")

    allowed = allowed_admin_emails()
    if allowed and email not in allowed:
        raise HTTPException(status_code=403, detail="這個 Google 帳戶不在允許名單內。")

    request.session["admin_email"] = email
    next_url = safe_next_url(str(request.session.pop("login_next", "/admin")))
    return RedirectResponse(next_url, status_code=303)


@app.post("/auth/logout")
def auth_logout(request: Request) -> RedirectResponse:
    request.session.clear()
    return RedirectResponse("/admin", status_code=303)


def effective_status(row: dict[str, Any]) -> str:
    if row.get("admin_status"):
        if row["admin_status"] == "taken":
            return "pulled"
        return row["admin_status"]
    if row.get("kind") == "vip-reserved":
        return "vip_available"
    if is_system_closed_section(row.get("section_name")):
        return "closed"
    if row.get("taken"):
        return "public_sold"
    return "public_available"


def is_system_closed_section(section_name: Any) -> bool:
    text = str(section_name or "")
    return any(pattern in text for pattern in SYSTEM_CLOSED_SECTION_PATTERNS)


def computed_status_sql() -> str:
    return """
        CASE
          WHEN s.kind = 'vip-reserved' THEN 'vip_available'
          WHEN COALESCE(s.section_name, '') LIKE '%保留%' THEN 'closed'
          WHEN COALESCE(s.section_name, '') LIKE '%評鑑席%' THEN 'closed'
          WHEN COALESCE(s.section_name, '') LIKE '%館方工作席%' THEN 'closed'
          WHEN s.taken = 1 THEN 'public_sold'
          ELSE 'public_available'
        END
    """


def effective_status_sql() -> str:
    return f"""
        COALESCE(
          CASE
            WHEN o.admin_status = 'taken' THEN 'pulled'
            ELSE o.admin_status
          END,
          {computed_status_sql()}
        )
    """


def event_or_404(db: Connection, event_id: str) -> dict[str, Any]:
    event = row_to_dict(db.execute("SELECT * FROM events WHERE event_id = ?", (event_id,)).fetchone())
    if not event:
        raise HTTPException(status_code=404, detail="Event not found.")
    return event


def status_reason(row: dict[str, Any], status: str) -> str:
    assignee = str(row.get("assignee_name") or "").strip()
    section_name = str(row.get("section_name") or "").strip()
    admin_status = row.get("admin_status")

    if status == "vip_assigned":
        if assignee:
            return assignee
        return "已分配"
    if status == "taken":
        if assignee:
            return f"內部標記為已預訂，受配者：{assignee}。"
        return "內部標記為已預訂。"
    if status == "closed":
        if not admin_status and is_system_closed_section(section_name):
            return f"票區名稱為「{section_name}」，依系統規則不開放販售。"
        return "內部標記為不開放。"
    if status == "public_sold":
        return "已在opentix售出不可調度"
    if status == "pulled":
        return "已調票至內部控管，尚未指定受配者。"
    if status == "vip_available":
        return "Friends VIP 保留席，可調票或指定給貴賓。"
    return "仍在opentix販售不可調度"


def seat_is_editable(row: dict[str, Any], status: str) -> bool:
    return status in {"pulled", "vip_assigned"}


def locked_reason(row: dict[str, Any], status: str) -> str:
    if seat_is_editable(row, status):
        return ""
    if status in {"public_available", "vip_available"} and not row.get("taken"):
        return "仍在opentix販售不可調度"
    if status in {"public_sold", "vip_available"}:
        return "已在opentix售出不可調度"
    if status == "closed":
        return "此座位屬於技術保留、評鑑、館方工作席或其他不開放票區。"
    return "此狀態不能從內部後台改動。"


def allowed_actions(row: dict[str, Any], status: str) -> list[dict[str, str]]:
    if not seat_is_editable(row, status):
        return []
    return [{"value": value, "label": STATUS_LABELS[value]} for value in EDITABLE_STATUS_VALUES]


def admin_seat(row: dict[str, Any]) -> dict[str, Any]:
    status = row.get("effective_status") or effective_status(row)
    editable = seat_is_editable(row, status)
    return {
        "svgId": row["svg_id"],
        "key": f"{row['floor_id']}|{row['row_id']}|{row['seat_number']}",
        "floorId": row["floor_id"],
        "rowId": row["row_id"],
        "number": row["seat_number"],
        "sectionId": row["section_id"],
        "sectionName": row["section_name"],
        "price": row["price"],
        "kind": row["kind"],
        "color": row["color"],
        "opentixStatus": row["opentix_status"],
        "opentixTaken": bool(row["taken"]),
        "takenSource": row["taken_source"],
        "rX": row["r_x"],
        "rY": row["r_y"],
        "adminStatus": row["admin_status"],
        "effectiveStatus": status,
        "statusLabel": STATUS_LABELS.get(status, status),
        "statusReason": status_reason(row, status),
        "editable": editable,
        "lockedReason": "" if editable else locked_reason(row, status),
        "allowedActions": allowed_actions(row, status),
        "isOverride": row["admin_status"] is not None,
        "overrideSource": row["override_source"],
        "sourceRecordId": row["source_record_id"],
        "updatedBy": row["updated_by"],
        "updatedAt": row["override_updated_at"],
        "assigneeName": row["assignee_name"] or "",
        "note": row["override_note"] or "",
    }


def admin_seat_select_sql(where_clause: str = "s.event_id = ?") -> str:
    return f"""
        SELECT
          s.*,
          o.admin_status,
          o.assignee_name,
          o.note AS override_note,
          o.source AS override_source,
          o.source_record_id,
          o.updated_by,
          o.updated_at AS override_updated_at,
          {effective_status_sql()} AS effective_status
        FROM seats s
        LEFT JOIN seat_overrides o
          ON o.event_id = s.event_id
         AND o.floor_id = s.floor_id
         AND o.row_id = s.row_id
         AND o.seat_number = s.seat_number
        WHERE {where_clause}
    """


def admin_seat_or_404(
    db: Connection,
    event_id: str,
    floor_id: str,
    row_id: str,
    seat_number: str,
) -> dict[str, Any]:
    row = row_to_dict(
        db.execute(
            admin_seat_select_sql(
                "s.event_id = ? AND s.floor_id = ? AND s.row_id = ? AND s.seat_number = ?"
            ),
            (event_id, floor_id, row_id, seat_number),
        ).fetchone()
    )
    if not row:
        raise HTTPException(status_code=404, detail="找不到座位。")
    return row


def update_seat_override(
    db: Connection,
    event_id: str,
    floor_id: str,
    row_id: str,
    seat_number: str,
    admin_status: str,
    assignee_name: str,
    note: str,
    admin_email: str,
    *,
    commit: bool = True,
    action: str = "update_override",
) -> None:
    key = (event_id, floor_id, row_id, seat_number)
    current = admin_seat_or_404(db, event_id, floor_id, row_id, seat_number)
    current_status = current.get("effective_status") or effective_status(current)
    if not seat_is_editable(current, current_status):
        raise HTTPException(status_code=400, detail=locked_reason(current, current_status))
    if admin_status not in EDITABLE_STATUS_VALUES:
        raise HTTPException(status_code=400, detail="這個座位不能套用此狀態。")
    if admin_status == "vip_assigned" and not assignee_name.strip():
        raise HTTPException(status_code=400, detail="指定座位時請填寫受配者。")
    if admin_status == "pulled":
        assignee_name = ""

    old_override = row_to_dict(
        db.execute(
            """
            SELECT * FROM seat_overrides
            WHERE event_id = ? AND floor_id = ? AND row_id = ? AND seat_number = ?
            """,
            key,
        ).fetchone()
    )

    db.execute(
        """
        INSERT INTO seat_overrides (
          event_id, floor_id, row_id, seat_number,
          admin_status, assignee_name, note, source, updated_by, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, 'admin-ui', ?, CURRENT_TIMESTAMP)
        ON CONFLICT(event_id, floor_id, row_id, seat_number) DO UPDATE SET
          admin_status = excluded.admin_status,
          assignee_name = excluded.assignee_name,
          note = excluded.note,
          source = excluded.source,
          updated_by = excluded.updated_by,
          updated_at = CURRENT_TIMESTAMP
        """,
        (*key, admin_status, assignee_name.strip() or None, note.strip() or None, admin_email),
    )
    new_value = {
        "admin_status": admin_status,
        "assignee_name": assignee_name.strip() or None,
        "note": note.strip() or None,
    }

    db.execute(
        """
        INSERT INTO audit_log (
          event_id, floor_id, row_id, seat_number,
          action, old_value, new_value, actor_email
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            *key,
            action,
            json.dumps(old_override, ensure_ascii=False),
            json.dumps(new_value, ensure_ascii=False),
            admin_email,
        ),
    )
    if commit:
        db.commit()


def public_seat(row: dict[str, Any]) -> dict[str, Any]:
    status = effective_status(row)
    public_status = "vip_available" if status == "pulled" else status
    is_taken = status in {"vip_assigned", "taken", "public_sold", "closed"}
    return {
        "svgId": row["svg_id"],
        "floorId": row["floor_id"],
        "rowId": row["row_id"],
        "number": row["seat_number"],
        "sectionId": row["section_id"],
        "sectionName": row["section_name"],
        "price": row["price"],
        "kind": row["kind"],
        "color": row["color"],
        "taken": is_taken,
        "availability": "taken" if is_taken else "available",
        "label": PUBLIC_STATUS_LABELS.get(public_status, public_status),
    }


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
def root() -> RedirectResponse:
    return RedirectResponse("/admin", status_code=302)


@app.get("/public-seatmap/{event_id}")
def public_seatmap(event_id: str, db: Connection = Depends(get_db)) -> dict[str, Any]:
    event = event_or_404(db, event_id)
    rows = db.execute(
        """
        SELECT s.*, o.admin_status, o.assignee_name, o.note AS override_note
        FROM seats s
        LEFT JOIN seat_overrides o
          ON o.event_id = s.event_id
         AND o.floor_id = s.floor_id
         AND o.row_id = s.row_id
         AND o.seat_number = s.seat_number
        WHERE s.event_id = ?
        ORDER BY s.floor_id, CAST(s.row_id AS INTEGER), s.row_id, CAST(s.seat_number AS INTEGER), s.seat_number
        """,
        (event_id,),
    ).fetchall()
    return {
        "event": {
            "eventId": event["event_id"],
            "programId": event["program_id"],
            "date": event["date_label"],
            "title": event["title"],
            "venue": event["venue"],
        },
        "seats": [public_seat(dict(row)) for row in rows],
    }


@app.get("/admin", response_class=HTMLResponse)
def admin_events(
    request: Request,
    db: Connection = Depends(get_db),
    admin_email: str = Depends(require_admin),
) -> HTMLResponse:
    status_expr = effective_status_sql()
    events = rows_to_dicts(
        db.execute(
            f"""
            SELECT
              e.*,
              COUNT(s.seat_number) AS seat_count,
              SUM(CASE WHEN {status_expr} IN ('pulled', 'vip_available') THEN 1 ELSE 0 END) AS vip_available_count,
              SUM(CASE WHEN {status_expr} = 'vip_assigned' THEN 1 ELSE 0 END) AS assigned_count,
              SUM(CASE WHEN {status_expr} = 'public_sold' THEN 1 ELSE 0 END) AS public_sold_count
            FROM events e
            LEFT JOIN seats s ON s.event_id = e.event_id
            LEFT JOIN seat_overrides o
              ON o.event_id = s.event_id
             AND o.floor_id = s.floor_id
             AND o.row_id = s.row_id
             AND o.seat_number = s.seat_number
            GROUP BY e.event_id
            ORDER BY e.sort_order
            """
        ).fetchall()
    )
    return templates.TemplateResponse(
        request,
        "events.html",
        {"events": events, "admin_email": admin_email},
    )


@app.get("/admin/events/{event_id}", response_class=HTMLResponse)
def admin_event_detail(
    request: Request,
    event_id: str,
    q: str = "",
    status: str = "",
    floor: str = "",
    db: Connection = Depends(get_db),
    admin_email: str = Depends(require_admin),
) -> HTMLResponse:
    event = event_or_404(db, event_id)

    filters = ["s.event_id = ?"]
    params: list[Any] = [event_id]
    if q:
        like = f"%{q}%"
        filters.append(
            "(s.floor_id LIKE ? OR s.row_id LIKE ? OR s.seat_number LIKE ? OR s.section_name LIKE ? OR o.assignee_name LIKE ?)"
        )
        params.extend([like, like, like, like, like])
    if floor:
        filters.append("s.floor_id = ?")
        params.append(floor)
    if status:
        filters.append(
            f"{effective_status_sql()} = ?"
        )
        params.append(status)

    seats = rows_to_dicts(
        db.execute(
            admin_seat_select_sql(" AND ".join(filters))
            + """
            ORDER BY s.floor_id, CAST(s.row_id AS INTEGER), s.row_id, CAST(s.seat_number AS INTEGER), s.seat_number
            LIMIT 500
            """,
            params,
        ).fetchall()
    )
    floors = [row["floor_id"] for row in db.execute("SELECT DISTINCT floor_id FROM seats WHERE event_id = ? ORDER BY floor_id", (event_id,))]
    return templates.TemplateResponse(
        request,
        "event.html",
        {
            "event": event,
            "seats": seats,
            "floors": floors,
            "status_options": STATUS_LABELS,
            "q": q,
            "status": status,
            "floor": floor,
            "admin_email": admin_email,
        },
    )


@app.get("/admin/events/{event_id}/seatmap.svg")
def admin_event_seatmap_svg(
    event_id: str,
    db: Connection = Depends(get_db),
    _: str = Depends(require_admin),
) -> Response:
    event_or_404(db, event_id)
    svg_path = REPO_ROOT / "assets" / "opentix" / f"{event_id}-seatmap.svg"
    if not svg_path.exists():
        raise HTTPException(status_code=404, detail="找不到座位圖 SVG。")
    return Response(svg_path.read_text(encoding="utf-8"), media_type="image/svg+xml")


@app.get("/admin/events/{event_id}/seats.json")
def admin_event_seats_json(
    event_id: str,
    db: Connection = Depends(get_db),
    admin_email: str = Depends(require_admin),
) -> dict[str, Any]:
    event = event_or_404(db, event_id)
    rows = rows_to_dicts(
        db.execute(
            admin_seat_select_sql()
            + """
            ORDER BY s.floor_id, CAST(s.row_id AS INTEGER), s.row_id, CAST(s.seat_number AS INTEGER), s.seat_number
            """,
            (event_id,),
        ).fetchall()
    )
    return {
        "event": {
            "eventId": event["event_id"],
            "programId": event["program_id"],
            "date": event["date_label"],
            "title": event["title"],
            "venue": event["venue"],
        },
        "adminEmail": admin_email,
        "statusOptions": STATUS_LABELS,
        "editableStatusOptions": {value: STATUS_LABELS[value] for value in EDITABLE_STATUS_VALUES},
        "seats": [admin_seat(row) for row in rows],
    }


def seat_identity_from_payload(payload: dict[str, Any]) -> tuple[str, str, str]:
    floor_id = str(payload.get("floorId") or payload.get("floor_id") or "").strip()
    row_id = str(payload.get("rowId") or payload.get("row_id") or "").strip()
    seat_number = str(payload.get("number") or payload.get("seatNumber") or payload.get("seat_number") or "").strip()

    if not floor_id or not row_id or not seat_number:
        raise HTTPException(status_code=400, detail="座位資料缺少樓層、排或號碼。")
    return floor_id, row_id, seat_number


@app.post("/admin/events/{event_id}/seats.json")
async def update_seat_json(
    request: Request,
    event_id: str,
    db: Connection = Depends(get_db),
    admin_email: str = Depends(require_admin),
) -> dict[str, Any]:
    payload = await request.json()
    admin_status = str(payload.get("adminStatus") or payload.get("admin_status") or "clear").strip()
    assignee_name = str(payload.get("assigneeName") or payload.get("assignee_name") or "").strip()
    note = str(payload.get("note") or "").strip()
    keep_existing_assignee = bool(payload.get("keepExistingAssignee") or payload.get("keep_existing_assignee"))
    keep_existing_note = bool(payload.get("keepExistingNote") or payload.get("keep_existing_note"))
    seat_payloads = payload.get("seats")

    if isinstance(seat_payloads, list):
        if not seat_payloads:
            raise HTTPException(status_code=400, detail="請至少選取一個座位。")
        if len(seat_payloads) > 300:
            raise HTTPException(status_code=400, detail="一次最多可批次修改 300 個座位。")

        identities: list[tuple[str, str, str]] = []
        seen: set[tuple[str, str, str]] = set()
        for item in seat_payloads:
            if not isinstance(item, dict):
                raise HTTPException(status_code=400, detail="批次座位資料格式不正確。")
            identity = seat_identity_from_payload(item)
            if identity in seen:
                continue
            seen.add(identity)
            identities.append(identity)

        try:
            for floor_id, row_id, seat_number in identities:
                current_seat = admin_seat(admin_seat_or_404(db, event_id, floor_id, row_id, seat_number))
                update_seat_override(
                    db,
                    event_id,
                    floor_id,
                    row_id,
                    seat_number,
                    admin_status,
                    current_seat["assigneeName"] if keep_existing_assignee else assignee_name,
                    current_seat["note"] if keep_existing_note else note,
                    admin_email,
                    commit=False,
                    action="batch_update_override",
                )
            db.commit()
        except Exception:
            db.rollback()
            raise

        seats = [
            admin_seat(admin_seat_or_404(db, event_id, floor_id, row_id, seat_number))
            for floor_id, row_id, seat_number in identities
        ]
        return {"seats": seats}

    floor_id, row_id, seat_number = seat_identity_from_payload(payload)
    current_seat = admin_seat(admin_seat_or_404(db, event_id, floor_id, row_id, seat_number))

    update_seat_override(
        db,
        event_id,
        floor_id,
        row_id,
        seat_number,
        admin_status,
        current_seat["assigneeName"] if keep_existing_assignee else assignee_name,
        current_seat["note"] if keep_existing_note else note,
        admin_email,
    )
    seat = admin_seat(admin_seat_or_404(db, event_id, floor_id, row_id, seat_number))
    return {"seat": seat}


@app.post("/admin/events/{event_id}/seats")
def update_seat(
    event_id: str,
    floor_id: str = Form(...),
    row_id: str = Form(...),
    seat_number: str = Form(...),
    admin_status: str = Form(...),
    assignee_name: str = Form(""),
    note: str = Form(""),
    next_url: str = Form("/admin"),
    db: Connection = Depends(get_db),
    admin_email: str = Depends(require_admin),
) -> RedirectResponse:
    update_seat_override(
        db,
        event_id,
        floor_id,
        row_id,
        seat_number,
        admin_status,
        assignee_name,
        note,
        admin_email,
    )

    if not next_url.startswith("/admin"):
        next_url = f"/admin/events/{event_id}"
    return RedirectResponse(next_url, status_code=303)
