#!/usr/bin/env python3
"""
Regenerate public Friends of Opus Formosa OPENTIX seat-map snapshots.

Admin credentials and tokens are read from environment variables or GitHub
Actions secrets. Never commit OPENTIX credentials, refresh tokens, access
tokens, HAR files, or browser storage snapshots.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, OrderedDict
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RULES = ROOT / "seatmap" / "_dev" / "opentix-sync-rules.json"
TAIPEI = ZoneInfo("Asia/Taipei")
USER_AGENT = "OpusFormosaSeatmapSync/1.0 (+https://opusformosa.org)"


class SyncError(RuntimeError):
    pass


class Unauthorized(SyncError):
    pass


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_text(path: Path, content: str, dry_run: bool) -> None:
    if dry_run:
        print(f"[dry-run] would write {path.relative_to(ROOT)}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, payload: Any, dry_run: bool) -> None:
    content = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    write_text(path, content, dry_run)


def request(url: str, headers: dict[str, str] | None = None, data: bytes | None = None) -> bytes:
    request_headers = {
        "Accept": "application/json,text/plain,*/*",
        "User-Agent": USER_AGENT,
    }
    if headers:
        request_headers.update(headers)
    req = urllib.request.Request(
        url,
        data=data,
        headers=request_headers,
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")[:500]
        if exc.code == 401:
            raise Unauthorized(f"HTTP 401 while fetching {redact_sensitive_url(url)}") from exc
        raise SyncError(f"HTTP {exc.code} while fetching {redact_sensitive_url(url)}: {body}") from exc
    except urllib.error.URLError as exc:
        raise SyncError(f"Failed to fetch {redact_sensitive_url(url)}: {exc}") from exc


def fetch_text(url: str) -> str:
    return request(url).decode("utf-8")


class OpentixAuth:
    def __init__(self, config: dict[str, Any]):
        fetch_config = config["fetch"]
        self.cognito_url = fetch_config["cognitoUrl"]
        self.client_id = os.environ.get("OPENTIX_COGNITO_CLIENT_ID") or fetch_config["cognitoClientId"]
        self.login_url = fetch_config["adminLoginUrl"]
        self.access_token = os.environ.get("OPENTIX_ADMIN_ACCESS_TOKEN", "").strip()
        authorization = os.environ.get("OPENTIX_ADMIN_AUTHORIZATION", "").strip()
        if authorization.lower().startswith("bearer "):
            self.access_token = authorization.split(" ", 1)[1].strip()
        self.refresh_token = os.environ.get("OPENTIX_COGNITO_REFRESH_TOKEN", "").strip()

    def authorization_header(self) -> str:
        token = self.get_access_token()
        return f"Bearer {token}"

    def get_access_token(self) -> str:
        if self.access_token:
            return self.access_token
        if self.refresh_token:
            try:
                self.refresh_access_token()
                return self.access_token
            except SyncError as exc:
                print(f"[auth] refresh token failed; falling back to headless login ({exc})", file=sys.stderr)
        self.login_with_playwright()
        return self.access_token

    def refresh_access_token(self) -> None:
        if not self.refresh_token:
            raise SyncError("OPENTIX_COGNITO_REFRESH_TOKEN is not set.")
        payload = {
            "AuthFlow": "REFRESH_TOKEN_AUTH",
            "ClientId": self.client_id,
            "AuthParameters": {
                "REFRESH_TOKEN": self.refresh_token,
            },
        }
        headers = {
            "Content-Type": "application/x-amz-json-1.1",
            "Origin": "https://opt.console.opentix.life",
            "Referer": "https://opt.console.opentix.life/",
            "X-Amz-Target": "AWSCognitoIdentityProviderService.InitiateAuth",
            "X-Amz-User-Agent": "aws-amplify/0.1.x js",
        }
        try:
            response = json.loads(request(self.cognito_url, headers=headers, data=json.dumps(payload).encode("utf-8")).decode("utf-8"))
        except Unauthorized as exc:
            raise SyncError("Cognito refresh was unauthorized.") from exc
        except SyncError:
            raise
        except Exception as exc:
            raise SyncError(f"Cognito refresh failed: {exc}") from exc
        result = response.get("AuthenticationResult") or {}
        access_token = result.get("AccessToken")
        if not access_token:
            raise SyncError("Cognito refresh response did not contain AccessToken.")
        self.access_token = access_token
        print("[auth] refreshed OPENTIX access token")

    def login_with_playwright(self) -> None:
        username = os.environ.get("OPENTIX_ADMIN_USERNAME")
        password = os.environ.get("OPENTIX_ADMIN_PASSWORD")
        if not username or not password:
            raise SyncError(
                "Missing OPENTIX auth. Set OPENTIX_COGNITO_REFRESH_TOKEN, or set both OPENTIX_ADMIN_USERNAME and OPENTIX_ADMIN_PASSWORD."
            )
        helper = ROOT / "seatmap" / "_dev" / "opentix-admin-login.cjs"
        node = os.environ.get("OPENTIX_NODE_BIN") or "node"
        env = os.environ.copy()
        env["OPENTIX_ADMIN_LOGIN_URL"] = self.login_url
        try:
            result = subprocess.run(
                [node, str(helper)],
                cwd=str(ROOT),
                env=env,
                check=True,
                capture_output=True,
                text=True,
                timeout=140,
            )
        except FileNotFoundError as exc:
            raise SyncError("Node.js is required for OPENTIX headless login.") from exc
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or exc.stdout or "").strip()
            raise SyncError(f"OPENTIX headless login failed: {detail}") from exc
        except subprocess.TimeoutExpired as exc:
            raise SyncError("OPENTIX headless login timed out.") from exc
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise SyncError("OPENTIX headless login returned invalid JSON.") from exc
        access_token = payload.get("accessToken")
        if not access_token:
            raise SyncError("OPENTIX headless login did not return accessToken.")
        self.access_token = access_token
        if payload.get("refreshToken"):
            self.refresh_token = payload["refreshToken"]
        print("[auth] logged in to OPENTIX admin with headless browser")

    def force_refresh_or_login(self) -> None:
        self.access_token = ""
        if self.refresh_token:
            try:
                self.refresh_access_token()
                return
            except SyncError as exc:
                print(f"[auth] refresh after 401 failed; falling back to headless login ({exc})", file=sys.stderr)
        self.login_with_playwright()


def fetch_admin_json(url: str, auth: OpentixAuth) -> Any:
    headers = {
        "Authorization": auth.authorization_header(),
        "Content-Type": "application/json;charset=utf-8",
        "Origin": "https://opt.console.opentix.life",
        "Referer": "https://opt.console.opentix.life/",
    }
    try:
        return json.loads(request(url, headers=headers).decode("utf-8"))
    except Unauthorized:
        auth.force_refresh_or_login()
        headers["Authorization"] = auth.authorization_header()
        return json.loads(request(url, headers=headers).decode("utf-8"))


def redact_sensitive_url(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    query = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    redacted = [(key, "***" if key.lower() in {"code", "token"} else value) for key, value in query]
    return urllib.parse.urlunsplit(parsed._replace(query=urllib.parse.urlencode(redacted)))


def unwrap_api_payload(payload: Any) -> Any:
    if isinstance(payload, dict):
        for key in ("result", "data"):
            if key in payload:
                return payload[key]
    return payload


def html_attr(value: Any) -> str:
    if value is None:
        return ""
    return escape(str(value), quote=True)


def slug_kind(kind: str) -> str:
    return re.sub(r"[^a-z0-9_-]+", "-", kind.lower()).strip("-") or "seat"


def first_present(obj: dict[str, Any], keys: tuple[str, ...], default: Any = None) -> Any:
    for key in keys:
        if key in obj and obj[key] is not None:
            return obj[key]
    return default


def normalize_id(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() in {"none", "null", "undefined"}:
        return ""
    return text


def normalize_price(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def expand_ranges(values: list[Any] | None) -> set[str] | None:
    if values is None:
        return None
    expanded: set[str] = set()
    for value in values:
        text = normalize_id(value)
        match = re.fullmatch(r"(-?\d+)\s*-\s*(-?\d+)", text)
        if match:
            start = int(match.group(1))
            end = int(match.group(2))
            step = 1 if end >= start else -1
            for item in range(start, end + step, step):
                expanded.add(str(item))
        else:
            expanded.add(text)
    return expanded


def selector_matches(selector: dict[str, Any], seat: dict[str, Any]) -> bool:
    floor = selector.get("floor")
    if floor is not None and normalize_id(floor) != normalize_id(seat.get("floorId")):
        return False
    rows = expand_ranges(selector.get("rows"))
    if rows is not None and normalize_id(seat.get("rowId")) not in rows:
        return False
    numbers = expand_ranges(selector.get("numbers"))
    if numbers is not None and normalize_id(seat.get("number")) not in numbers:
        return False
    return True


def flatten_group_sections(group_sections: Any) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []

    def visit(node: Any) -> None:
        if isinstance(node, list):
            for item in node:
                visit(item)
            return
        if isinstance(node, dict):
            if "id" in node and ("name" in node or "price" in node or "color" in node):
                sections.append(node)
                return
            for value in node.values():
                visit(value)

    visit(group_sections)
    deduped: OrderedDict[str, dict[str, Any]] = OrderedDict()
    for section in sections:
        section_id = normalize_id(section.get("id"))
        if section_id and section_id not in deduped:
            deduped[section_id] = section
    return list(deduped.values())


def section_from_opentix(raw: dict[str, Any]) -> dict[str, Any]:
    price = normalize_price(raw.get("price"))
    original_price = None
    price_plan_name = None

    for plan in raw.get("pricePlans") or []:
        if isinstance(plan, dict) and plan.get("currentPrice") is not None:
            current_price = normalize_price(plan.get("currentPrice"))
            if current_price is not None:
                original_price = price
                price = current_price
                price_plan_name = plan.get("name")
                break

    name = raw.get("name") or "未命名票區"
    if price_plan_name and original_price and price and price != original_price:
        if str(price) not in name:
            name = f"{price_plan_name}{price}元（原價{original_price}）"

    section = {
        "id": normalize_id(raw.get("id")),
        "name": name,
        "price": price,
        "color": raw.get("color") or "#999999",
        "kind": "public",
        "source": "opentix-price-section",
    }
    if original_price and original_price != price:
        section["originalPrice"] = original_price
    if price_plan_name:
        section["pricePlanName"] = price_plan_name
    return section


def extract_seat_entries(payload: Any) -> list[dict[str, Any]]:
    payload = unwrap_api_payload(payload)
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        raise SyncError("OPENTIX seats payload is not a list or object.")

    for key in ("seats", "seatList", "eventSeats", "items"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]

    found: list[dict[str, Any]] = []

    def visit(node: Any) -> None:
        if isinstance(node, list):
            for item in node:
                visit(item)
            return
        if isinstance(node, dict):
            keys = set(node)
            if {"sectionId", "rowId"} & keys and {"number", "seatNo", "seatNumber"} & keys:
                found.append(node)
                return
            for value in node.values():
                visit(value)

    visit(payload)
    if not found:
        raise SyncError("Could not find seat entries in OPENTIX seats payload.")
    return found


def normalize_seat(raw: dict[str, Any]) -> dict[str, Any]:
    floor = first_present(raw, ("floorId", "floorName", "floor", "areaName"), "")
    row = first_present(raw, ("rowId", "rowName", "row"), "")
    number = first_present(raw, ("number", "seatNo", "seatNumber", "seat"), "")
    svg_id = first_present(raw, ("svgId",), None)
    if not svg_id:
        svg_id = f"{floor}-{row}-{number}"
    seat = {
        "svgId": normalize_id(svg_id),
        "floorId": normalize_id(floor),
        "rowId": normalize_id(row),
        "number": normalize_id(number),
        "sectionId": normalize_id(first_present(raw, ("sectionId", "priceSectionId", "section"), "")),
        "status": raw.get("status"),
    }
    for key in ("eventId", "groupId", "rX", "rY", "autoSeatedOrderName", "autoSeatedOrderNumber", "parentSeatingChartId", "isConsecutive"):
        if key in raw:
            seat[key] = raw[key]
    return seat


def seat_lookup_key(seat: dict[str, Any]) -> tuple[str, str, str]:
    return (
        normalize_id(seat.get("floorId")),
        normalize_id(seat.get("rowId")),
        normalize_id(seat.get("number")),
    )


def fetch_public_seat_statuses(event_config: dict[str, Any], config: dict[str, Any]) -> dict[tuple[str, str, str], Any]:
    overlay_config = config.get("publicSeatStatusOverlay") or {}
    if not overlay_config.get("enabled", False):
        return {}

    fetch_config = config["fetch"]
    url_template = fetch_config.get("publicSeatStatusUrl")
    if not url_template:
        return {}

    event_id = event_config["eventId"]
    parent_seating_chart_id = str(event_config["parentSeatingChartId"])
    url = url_template.format(
        eventId=urllib.parse.quote(event_id),
        parentSeatingChartId=urllib.parse.quote(parent_seating_chart_id),
    )
    payload = json.loads(request(url).decode("utf-8"))
    entries = extract_seat_entries(payload)
    statuses: dict[tuple[str, str, str], Any] = {}
    for item in entries:
        seat = normalize_seat(item)
        key = seat_lookup_key(seat)
        if all(key):
            statuses[key] = seat.get("status")
    return statuses


def overlay_public_statuses(seats: list[dict[str, Any]], public_statuses: dict[tuple[str, str, str], Any]) -> int:
    if not public_statuses:
        return 0
    updated = 0
    for seat in seats:
        key = seat_lookup_key(seat)
        if key not in public_statuses:
            continue
        public_status = public_statuses[key]
        if seat.get("status") != public_status:
            seat["adminStatus"] = seat.get("status")
            seat["status"] = public_status
            updated += 1
        seat["statusSource"] = "opentix-public-seats-api"
    return updated


def display_title_for_header(event_config: dict[str, Any], program: dict[str, Any]) -> str:
    labels = event_config.get("labels") or {}
    title = labels.get("title") or program.get("name") or "Opus 音樂節"
    if "《" in title:
        return str(title)
    if "室內樂" in str(program.get("name", "")):
        series = "室內樂系列"
        if "I" in str(program.get("name", "")) and "歐陸" in str(title):
            series = "室內樂系列 I"
        elif "II" in str(program.get("name", "")) and "異鄉" in str(title):
            series = "室內樂系列 II"
        elif "III" in str(program.get("name", "")) and "弦間" in str(title):
            series = "室內樂系列 III"
        return f"{series}《{title}》"
    return f"Opus音樂節《{title}》"


def public_event_url(program_id: str) -> str:
    return f"https://www.opentix.life/event/{program_id}"


def override_matches(rule: dict[str, Any], seat: dict[str, Any]) -> bool:
    match = rule.get("match") or {}
    section_ids = {normalize_id(item) for item in match.get("sectionIds") or []}
    if section_ids and seat.get("sectionId") in section_ids:
        return True
    for selector in match.get("seatSelectors") or []:
        if selector_matches(selector, seat):
            return True
    return False


def pulled_record_matches(record: dict[str, Any], seat: dict[str, Any]) -> bool:
    if normalize_id(record.get("eventId")) != normalize_id(seat.get("eventId")):
        return False
    for selector in record.get("seatSelectors") or []:
        if selector_matches(selector, seat):
            return True
    return False


def pulled_records_for_event(config: dict[str, Any], event_id: str) -> list[dict[str, Any]]:
    return [
        record
        for record in config.get("pulledSeatRecords") or []
        if normalize_id(record.get("eventId")) == normalize_id(event_id)
    ]


STATUS_FIELDS = (
    "taken",
    "availability",
    "takenLabel",
    "takenSource",
    "takenNote",
    "takenRuleType",
    "publicSold",
)


def normalize_status(value: Any) -> str:
    return normalize_id(value).lower()


def status_matches(value: Any, statuses: list[Any]) -> bool:
    normalized = normalize_status(value)
    return any(normalized == normalize_status(status) for status in statuses)


def has_opentix_public_available_status(seat: dict[str, Any], config: dict[str, Any]) -> bool:
    raw_status = seat.get("status")
    if raw_status is None or normalize_id(raw_status) == "":
        return False
    policy = config.get("opentixAvailabilityMarkers") or {}
    available_statuses = policy.get("availableStatuses") or [0, "0"]
    return status_matches(raw_status, available_statuses)


def vip_override_is_blocked_by_public_sale(
    seat: dict[str, Any],
    display: dict[str, Any],
    config: dict[str, Any],
) -> bool:
    if display.get("kind", "vip-reserved") != "vip-reserved":
        return False
    return has_opentix_public_available_status(seat, config)


def apply_status_overrides(final_seats: list[dict[str, Any]], event_config: dict[str, Any], config: dict[str, Any]) -> list[str]:
    status_counts: Counter[str] = Counter()
    public_sale_block_counts: Counter[str] = Counter()
    for seat in final_seats:
        for key in STATUS_FIELDS:
            seat.pop(key, None)

        for rule in event_config.get("seatStatusOverrides") or []:
            if not override_matches(rule, seat):
                continue
            if has_opentix_public_available_status(seat, config):
                status_counts[rule["id"]] += 1
                public_sale_block_counts[rule["id"]] += 1
                break
            if rule.get("vipOnly", True) and seat.get("kind") != "vip-reserved":
                continue
            status_counts[rule["id"]] += 1
            status = rule.get("status") or "taken"
            if status == "taken":
                display = rule.get("display") or {}
                seat["taken"] = True
                seat["availability"] = "taken"
                seat["takenLabel"] = display.get("label") or "已預訂"
                seat["takenSource"] = display.get("source") or "opus-vip-taken-seat-map"
                seat["takenRuleType"] = "manual-seat-status-override"
                if display.get("note"):
                    seat["takenNote"] = display["note"]
            break

    errors: list[str] = []
    for rule in event_config.get("seatStatusOverrides") or []:
        expected = rule.get("expectedSeatCount")
        if expected is None:
            continue
        actual = status_counts[rule["id"]]
        if actual != expected:
            errors.append(f"{event_config['eventId']} {rule['id']}: expected {expected} taken seats, matched {actual}")
    for rule_id, count in public_sale_block_counts.items():
        print(
            f"[warning] {event_config['eventId']} {rule_id}: skipped {count} taken marker(s) because OPENTIX public status is available",
            file=sys.stderr,
        )
    return errors


def apply_opentix_availability_markers(final_seats: list[dict[str, Any]], config: dict[str, Any]) -> int:
    policy = config.get("opentixAvailabilityMarkers") or {}
    if not policy.get("enabled", False):
        return 0

    applies_to_kinds = {normalize_id(kind) for kind in policy.get("appliesToKinds") or ["public"]}
    available_statuses = policy.get("availableStatuses") or [0, "0"]
    unknown_status_means_available = bool(policy.get("unknownStatusMeansAvailable", True))
    display = policy.get("display") or {}
    count = 0

    for seat in final_seats:
        if seat.get("taken"):
            continue
        if normalize_id(seat.get("kind")) not in applies_to_kinds:
            continue
        raw_status = seat.get("status")
        if raw_status is None or normalize_id(raw_status) == "":
            if unknown_status_means_available:
                continue
        elif status_matches(raw_status, available_statuses):
            continue

        seat["taken"] = True
        seat["availability"] = "public_sold"
        seat["publicSold"] = True
        seat["takenLabel"] = display.get("label") or "OPENTIX 已售出／不可售"
        seat["takenSource"] = display.get("source") or "opentix-availability-marker"
        seat["takenRuleType"] = "opentix-availability-marker"
        if display.get("note"):
            seat["takenNote"] = display["note"]
        count += 1

    return count


def apply_pulled_seat_overrides(
    final_seats: list[dict[str, Any]],
    event_config: dict[str, Any],
    config: dict[str, Any],
) -> list[str]:
    records = pulled_records_for_event(config, event_config["eventId"])
    counts: Counter[str] = Counter()

    for seat in final_seats:
        seat.pop("pulledRecordId", None)
        for record in records:
            if not pulled_record_matches(record, seat):
                continue
            display = record.get("display") or {}
            counts[record["id"]] += 1
            if "originalSectionId" not in seat:
                seat["originalSectionId"] = seat.get("sectionId") or "opentix-unsectioned"
            if "originalSectionName" not in seat and seat.get("sectionName"):
                seat["originalSectionName"] = seat.get("sectionName")
            if "originalPrice" not in seat and seat.get("price") is not None:
                seat["originalPrice"] = seat.get("price")
            if normalize_id(seat.get("source")) == "opus-planned-internal-hold-seat-map":
                seat.pop("originalColor", None)
            reserved_unknown_color = config.get("displayDefaults", {}).get("reservedUnknownColor")
            if seat.get("originalColor") == reserved_unknown_color:
                seat.pop("originalColor", None)
            if (
                "originalColor" not in seat
                and seat.get("color")
                and seat.get("color") != reserved_unknown_color
                and not normalize_id(seat.get("source")).startswith("opus-")
            ):
                seat["originalColor"] = seat.get("color")
            section_id = display.get("sectionId") or record.get("ruleId") or record["id"]
            seat["sectionId"] = normalize_id(section_id)
            seat["sectionName"] = display.get("name") or record.get("label") or "Friends VIP 保留席"
            seat["price"] = display.get("price", record.get("price"))
            seat["kind"] = display.get("kind", "vip-reserved")
            original_price = normalize_price(seat.get("originalPrice"))
            has_ticket_price_color = bool(seat.get("originalColor")) and (
                bool(original_price and original_price > 0) or seat["price"] is None
            )
            if has_ticket_price_color:
                seat["color"] = seat["originalColor"]
            else:
                seat["color"] = display.get("color") or seat.get("originalColor") or "#FAAE17"
            seat["source"] = display.get("source", "opus-pulled-seat-map")
            seat["pulledRecordId"] = record["id"]
            if display.get("note") or record.get("note"):
                seat["note"] = display.get("note") or record.get("note")
            break

    errors: list[str] = []
    for record in records:
        expected = record.get("expectedSeatCount")
        if expected is None:
            continue
        actual = counts[record["id"]]
        if actual != expected:
            errors.append(f"{event_config['eventId']} {record['id']}: expected {expected} pulled seats, matched {actual}")
    return errors


def restore_stable_display_from_existing_snapshot(
    final_seats: list[dict[str, Any]],
    existing_snapshot: dict[str, Any] | None,
) -> None:
    if not existing_snapshot:
        return

    previous_seats = existing_snapshot.get("seats") or []
    previous_by_key = {seat_lookup_key(seat): seat for seat in previous_seats if all(seat_lookup_key(seat))}
    sections_by_id = {
        normalize_id(section.get("id")): section
        for section in existing_snapshot.get("sections") or []
        if section.get("id")
    }

    for seat in final_seats:
        previous = previous_by_key.get(seat_lookup_key(seat))
        if not previous:
            continue

        original_section_id = normalize_id(previous.get("originalSectionId"))
        if original_section_id:
            original_section = sections_by_id.get(original_section_id)
            seat["originalSectionId"] = original_section_id
            seat["originalSectionName"] = (
                original_section.get("name")
                if original_section
                else previous.get("originalSectionName")
            )
            seat["originalPrice"] = (
                original_section.get("price")
                if original_section and original_section.get("price") is not None
                else previous.get("originalPrice")
            )
            seat["originalColor"] = (
                original_section.get("color")
                if original_section and original_section.get("color")
                else previous.get("originalColor") or previous.get("color")
            )

        if normalize_id(seat.get("source")).startswith("opus-"):
            continue
        if normalize_id(previous.get("kind")) != "public":
            continue

        for field in ("sectionId", "sectionName", "price", "color", "kind", "source"):
            if previous.get(field) is not None:
                seat[field] = previous[field]


def apply_rules(
    seats: list[dict[str, Any]],
    official_sections: OrderedDict[str, dict[str, Any]],
    event_config: dict[str, Any],
    config: dict[str, Any],
    strict_counts: bool,
    existing_snapshot: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    fallback = config["fallbacks"]["seatsOnlySection"]
    defaults = config["displayDefaults"]
    override_counts: Counter[str] = Counter()
    public_sale_block_counts: Counter[str] = Counter()
    final: list[dict[str, Any]] = []

    for base_seat in seats:
        original_section_id = base_seat.get("sectionId") or "opentix-unsectioned"
        official = official_sections.get(original_section_id)
        if official:
            seat = {
                **base_seat,
                "sectionName": official["name"],
                "price": official.get("price"),
                "kind": official.get("kind", "public"),
                "color": official.get("color") or "#999999",
                "source": official.get("source", "opentix-price-section"),
            }
        else:
            seat = {
                **base_seat,
                "sectionId": original_section_id,
                "sectionName": fallback["name"],
                "price": fallback.get("price"),
                "kind": fallback["kind"],
                "color": fallback.get("color") or defaults["reservedUnknownColor"],
                "source": fallback["source"],
            }

        for rule in event_config.get("sectionOverrides") or []:
            if override_matches(rule, base_seat):
                display = rule["display"]
                override_counts[rule["id"]] += 1
                if vip_override_is_blocked_by_public_sale(base_seat, display, config):
                    public_sale_block_counts[rule["id"]] += 1
                    break
                seat["originalSectionId"] = original_section_id
                if official:
                    seat["originalSectionName"] = official.get("name")
                    seat["originalPrice"] = official.get("price")
                seat["sectionId"] = normalize_id(display.get("sectionId") or original_section_id or rule["id"])
                seat["sectionName"] = display["name"]
                seat["price"] = display.get("price")
                seat["kind"] = display.get("kind", "vip-reserved")
                seat["color"] = display.get("color") or "#FAAE17"
                seat["source"] = display.get("source", "opus-vip-section-map")
                if display.get("note"):
                    seat["note"] = display["note"]
                break

        final.append(seat)

    restore_stable_display_from_existing_snapshot(final, existing_snapshot)

    errors: list[str] = []
    for rule in event_config.get("sectionOverrides") or []:
        expected = rule.get("expectedSeatCount")
        if expected is None:
            continue
        actual = override_counts[rule["id"]]
        if actual != expected:
            errors.append(f"{event_config['eventId']} {rule['id']}: expected {expected} VIP seats, matched {actual}")
    errors.extend(apply_pulled_seat_overrides(final, event_config, config))
    errors.extend(apply_status_overrides(final, event_config, config))
    apply_opentix_availability_markers(final, config)
    if errors and strict_counts:
        raise SyncError("VIP rule count mismatch:\n" + "\n".join(errors))
    for error in errors:
        print(f"[warning] {error}", file=sys.stderr)
    for rule_id, count in public_sale_block_counts.items():
        print(
            f"[warning] {event_config['eventId']} {rule_id}: skipped {count} VIP override(s) because OPENTIX public status is available",
            file=sys.stderr,
        )

    return sorted(final, key=lambda seat: (seat.get("floorId", ""), natural_key(seat.get("rowId", "")), natural_key(seat.get("number", ""))))


def apply_section_overrides_to_existing(
    final_seats: list[dict[str, Any]],
    event_config: dict[str, Any],
    config: dict[str, Any],
) -> list[str]:
    override_counts: Counter[str] = Counter()
    public_sale_block_counts: Counter[str] = Counter()
    for seat in final_seats:
        for rule in event_config.get("sectionOverrides") or []:
            if not override_matches(rule, seat):
                continue
            display = rule["display"]
            override_counts[rule["id"]] += 1
            if vip_override_is_blocked_by_public_sale(seat, display, config):
                public_sale_block_counts[rule["id"]] += 1
                break
            if "originalSectionId" not in seat:
                seat["originalSectionId"] = seat.get("sectionId") or "opentix-unsectioned"
            if "originalSectionName" not in seat and seat.get("sectionName"):
                seat["originalSectionName"] = seat.get("sectionName")
            if "originalPrice" not in seat and seat.get("price") is not None:
                seat["originalPrice"] = seat.get("price")
            seat["sectionId"] = normalize_id(display.get("sectionId") or seat.get("originalSectionId") or rule["id"])
            seat["sectionName"] = display["name"]
            seat["price"] = display.get("price")
            seat["kind"] = display.get("kind", "vip-reserved")
            seat["color"] = display.get("color") or "#FAAE17"
            seat["source"] = display.get("source", "opus-vip-section-map")
            if display.get("note"):
                seat["note"] = display["note"]
            break

    errors: list[str] = []
    for rule in event_config.get("sectionOverrides") or []:
        expected = rule.get("expectedSeatCount")
        if expected is None:
            continue
        actual = override_counts[rule["id"]]
        if actual != expected:
            errors.append(f"{event_config['eventId']} {rule['id']}: expected {expected} VIP seats, matched {actual}")
    for rule_id, count in public_sale_block_counts.items():
        print(
            f"[warning] {event_config['eventId']} {rule_id}: skipped {count} VIP override(s) because OPENTIX public status is available",
            file=sys.stderr,
        )
    return errors


def restore_existing_seats_to_original_sections(
    final_seats: list[dict[str, Any]],
    existing_sections: list[dict[str, Any]],
) -> None:
    sections_by_id = {normalize_id(section.get("id")): section for section in existing_sections if section.get("id")}
    public_sections_by_name_price: dict[tuple[str, int | None], dict[str, Any]] = {}
    public_sections_by_name: dict[str, dict[str, Any]] = {}
    ambiguous_public_section_names: set[str] = set()
    for section in existing_sections:
        if normalize_id(section.get("kind")) != "public":
            continue
        name = normalize_id(section.get("name"))
        if not name:
            continue
        price = normalize_price(section.get("price"))
        public_sections_by_name_price[(name, price)] = section
        if name in public_sections_by_name:
            ambiguous_public_section_names.add(name)
        else:
            public_sections_by_name[name] = section

    for seat in final_seats:
        original_section_name = normalize_id(seat.get("originalSectionName"))
        original_price = normalize_price(seat.get("originalPrice"))
        original_section_id = normalize_id(seat.get("originalSectionId"))
        if not original_section_id and not original_section_name and original_price is None:
            continue

        original_section = sections_by_id.get(original_section_id) if original_section_id else None
        if not original_section and original_section_name:
            original_section = public_sections_by_name_price.get((original_section_name, original_price))
        if not original_section and original_section_name and original_section_name not in ambiguous_public_section_names:
            original_section = public_sections_by_name.get(original_section_name)

        seat["sectionId"] = original_section_id or (original_section.get("id") if original_section else None)
        seat["sectionName"] = (
            original_section.get("name")
            if original_section
            else seat.get("originalSectionName") or seat.get("sectionName") or "未命名票區"
        )
        seat["price"] = (
            original_section.get("price")
            if original_section
            else seat.get("originalPrice") if seat.get("originalPrice") is not None else seat.get("price")
        )
        seat["kind"] = original_section.get("kind", "public") if original_section else "public"
        seat["color"] = original_section.get("color", seat.get("color") or "#999999") if original_section else seat.get("color") or "#999999"
        seat["source"] = original_section.get("source", "opentix-price-section-restored") if original_section else "opentix-price-section-restored"
        seat.pop("note", None)


def natural_key(value: Any) -> tuple[int, Any]:
    text = normalize_id(value)
    if re.fullmatch(r"-?\d+", text):
        return (0, int(text))
    return (1, text)


def seat_section_bucket_id(seat: dict[str, Any]) -> str:
    if normalize_id(seat.get("kind")) == "public":
        return "|".join(
            [
                "generated-section",
                "public",
                normalize_id(seat.get("sectionName")) or "未命名票區",
                normalize_id(seat.get("price")),
                normalize_id(seat.get("color")),
            ]
        )
    section_id = normalize_id(seat.get("sectionId"))
    if section_id:
        return section_id
    return "|".join(
        [
            "generated-section",
            normalize_id(seat.get("kind")) or "unknown",
            normalize_id(seat.get("sectionName")) or "未命名票區",
            normalize_id(seat.get("price")),
            normalize_id(seat.get("color")),
        ]
    )


def build_sections(
    final_seats: list[dict[str, Any]],
    official_sections: OrderedDict[str, dict[str, Any]],
    event_config: dict[str, Any],
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    counts = Counter(seat_section_bucket_id(seat) for seat in final_seats)
    taken_counts = Counter(seat_section_bucket_id(seat) for seat in final_seats if seat.get("taken"))
    sample_by_section: dict[str, dict[str, Any]] = {}
    for seat in final_seats:
        sample_by_section.setdefault(seat_section_bucket_id(seat), seat)

    ordered_ids: list[str] = []
    for record in pulled_records_for_event(config, event_config["eventId"]):
        display = record.get("display") or {}
        section_id = normalize_id(display.get("sectionId") or record.get("ruleId") or record.get("id"))
        if section_id in counts and section_id not in ordered_ids:
            ordered_ids.append(section_id)
    for rule in event_config.get("sectionOverrides") or []:
        display = rule["display"]
        section_id = normalize_id(display.get("sectionId") or (rule.get("match", {}).get("sectionIds") or [rule["id"]])[0])
        if section_id in counts and section_id not in ordered_ids:
            ordered_ids.append(section_id)
    for section_id in official_sections:
        if section_id in counts and section_id not in ordered_ids:
            ordered_ids.append(section_id)
    for seat in final_seats:
        section_id = seat_section_bucket_id(seat)
        if section_id not in ordered_ids:
            ordered_ids.append(section_id)

    sections: list[dict[str, Any]] = []
    for section_id in ordered_ids:
        sample = sample_by_section[section_id]
        section = {
            "id": section_id,
            "name": sample.get("sectionName"),
            "price": sample.get("price"),
            "color": sample.get("color"),
            "kind": sample.get("kind"),
            "source": sample.get("source"),
            "seatCount": counts[section_id],
        }
        if sample.get("note"):
            section["note"] = sample["note"]
        if sample.get("originalSectionName"):
            section["originalName"] = sample.get("originalSectionName")
        if sample.get("originalPrice") is not None:
            section["originalPrice"] = sample.get("originalPrice")
        official = official_sections.get(normalize_id(sample.get("sectionId")))
        if official:
            for key in ("originalPrice", "pricePlanName"):
                if key in official and key not in section:
                    section[key] = official[key]
        if sample.get("source") == config["fallbacks"]["seatsOnlySection"]["source"] and "note" not in section:
            section["note"] = "Seat appears in OPENTIX seats API but not in public price sections and is not marked as Friends VIP."
        if taken_counts[section_id]:
            section["takenSeatCount"] = taken_counts[section_id]
        sections.append(section)
    return sections


def tag_attr(tag: str, name: str) -> str | None:
    match = re.search(rf'(?:^|\s){re.escape(name)}="([^"]*)"', tag)
    if not match:
        return None
    return match.group(1)


def number_attr(tag: str, name: str) -> float | None:
    value = tag_attr(tag, name)
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def fmt_svg_number(value: float) -> str:
    if value.is_integer():
        return str(int(value))
    return f"{value:.3f}".rstrip("0").rstrip(".")


def taken_mark_for_circle(circle_tag: str, seat: dict[str, Any], config: dict[str, Any]) -> str:
    cx = number_attr(circle_tag, "cx")
    cy = number_attr(circle_tag, "cy")
    radius = number_attr(circle_tag, "r")
    if cx is None or cy is None or radius is None:
        return ""
    delta = radius * 0.78
    transform = tag_attr(circle_tag, "transform")
    transform_attr = f' transform="{html_attr(transform)}"' if transform else ""
    stroke = html_attr(config["displayDefaults"].get("takenMarkStroke") or "#2f2417")
    stroke_width = fmt_svg_number(max(2.2, radius * 0.28))
    seat_id = html_attr(seat.get("svgId"))
    x1 = fmt_svg_number(cx - delta)
    y1 = fmt_svg_number(cy - delta)
    x2 = fmt_svg_number(cx + delta)
    y2 = fmt_svg_number(cy + delta)
    x3 = fmt_svg_number(cx - delta)
    y3 = fmt_svg_number(cy + delta)
    x4 = fmt_svg_number(cx + delta)
    y4 = fmt_svg_number(cy - delta)
    return (
        f'<line class="seat-taken-mark" data-seat-id="{seat_id}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"'
        f'{transform_attr} stroke="{stroke}" stroke-width="{stroke_width}" stroke-linecap="round" opacity="0.92" pointer-events="none"></line>'
        f'<line class="seat-taken-mark" data-seat-id="{seat_id}" x1="{x3}" y1="{y3}" x2="{x4}" y2="{y4}"'
        f'{transform_attr} stroke="{stroke}" stroke-width="{stroke_width}" stroke-linecap="round" opacity="0.92" pointer-events="none"></line>'
    )


def annotate_svg(svg: str, final_seats: list[dict[str, Any]], config: dict[str, Any]) -> str:
    defaults = config["displayDefaults"]
    seat_by_svg_id = {seat["svgId"]: seat for seat in final_seats}
    svg = re.sub(r'<line\b(?=[^>]*\bclass="seat-taken-mark")[^>]*></line>', "", svg)

    remove_attrs = re.compile(
        r'\s(?:class|stroke-width|stroke|fill|data-seat-id|data-floor|data-row|data-number|data-section-id|data-section-name|data-price|data-kind|data-taken|data-availability|data-taken-label|data-taken-source)="[^"]*"'
    )
    circle_re = re.compile(r"<circle\b(?=[^>]*\sid=\"([^\"]+)\")[^>]*(?:/>|></circle>)", re.DOTALL)

    def replacement(match: re.Match[str]) -> str:
        seat_id = match.group(1)
        seat = seat_by_svg_id.get(seat_id)
        if not seat:
            return match.group(0)
        tag = remove_attrs.sub("", match.group(0))
        kind = seat.get("kind") or "public"
        if kind == "vip-reserved":
            stroke = defaults["vipStroke"]
            stroke_width = "2"
        elif kind == "public":
            stroke = defaults["publicStroke"]
            stroke_width = "1"
        else:
            stroke = defaults["reservedStroke"]
            stroke_width = "1"
        attrs = (
            f' class="seat seat-{html_attr(slug_kind(kind))}{" seat-taken" if seat.get("taken") else ""}"'
            f' stroke-width="{stroke_width}"'
            f' stroke="{html_attr(stroke)}"'
            f' fill="{html_attr(seat.get("color"))}"'
            f' data-seat-id="{html_attr(seat.get("svgId"))}"'
            f' data-floor="{html_attr(seat.get("floorId"))}"'
            f' data-row="{html_attr(seat.get("rowId"))}"'
            f' data-number="{html_attr(seat.get("number"))}"'
            f' data-section-id="{html_attr(seat.get("sectionId"))}"'
            f' data-section-name="{html_attr(seat.get("sectionName"))}"'
            f' data-price="{html_attr(seat.get("price"))}"'
            f' data-kind="{html_attr(kind)}"'
        )
        if seat.get("taken"):
            attrs += (
                ' data-taken="true"'
                ' data-availability="taken"'
                f' data-taken-label="{html_attr(seat.get("takenLabel") or "已預訂")}"'
                f' data-taken-source="{html_attr(seat.get("takenSource") or "")}"'
            )
        if tag.endswith("/>"):
            circle_tag = tag[:-2] + attrs + "/>"
        elif tag.endswith("</circle>"):
            opening_tag = tag[: -len("</circle>")]
            circle_tag = opening_tag[:-1] + attrs + "></circle>"
        else:
            circle_tag = tag[:-1] + attrs + ">"
        if seat.get("taken"):
            return circle_tag + taken_mark_for_circle(circle_tag, seat, config)
        return circle_tag

    return circle_re.sub(replacement, svg)


def format_money(value: int | None) -> str:
    if value is None:
        return "未公開定價"
    return f"NT${value:,}"


def build_note(sections: list[dict[str, Any]], final_seats: list[dict[str, Any]]) -> str:
    vip_summary: OrderedDict[tuple[str, int | None], int] = OrderedDict()
    for section in sections:
        if section.get("kind") != "vip-reserved":
            continue
        key = (section.get("name") or "VIP 保留席", section.get("price"))
        vip_summary[key] = vip_summary.get(key, 0) + int(section.get("seatCount") or 0)

    if not vip_summary:
        vip_text = "Friends VIP 保留席"
    else:
        parts = []
        for (name, price), count in vip_summary.items():
            label = f"{format_money(price)} VIP 保留席" if price is not None else str(name)
            parts.append(f"{label}，共 {count} 席")
        vip_text = "；".join(parts)
    taken_count = sum(1 for seat in final_seats if seat.get("taken"))
    opentix_taken_count = sum(1 for seat in final_seats if seat.get("takenSource") == "opentix-availability-marker")
    if taken_count and opentix_taken_count:
        taken_text = f"打叉座位為已預訂或 OPENTIX 已不可售席次（{taken_count} 席）；"
    elif taken_count:
        taken_text = f"打叉座位為已預訂席次（{taken_count} 席）；"
    else:
        taken_text = ""
    return (
        "此頁由 OPENTIX 最新座位資料同步製作，用於 Friends of Opus Formosa 洽詢席位。"
        f"深色外框標示為 {vip_text}；{taken_text}其餘票區與不可售狀態依 OPENTIX 最新資料顯示；"
        "實際可安排座位仍以 Opus Formosa 團隊回覆為準。"
    )


def build_legend(sections: list[dict[str, Any]]) -> str:
    rows = []
    for section in sections:
        count_text = f"{section.get('seatCount')} 席"
        if section.get("takenSeatCount"):
            count_text += f"／已預訂 {section.get('takenSeatCount')} 席"
        section_key = "|".join(
            [
                str(section.get("kind") or ""),
                str(section.get("name") or ""),
                str(section.get("color") or ""),
            ]
        )
        rows.append(
            "          <li class=\"legend-item\" data-kind=\"{kind}\" data-section-key=\"{section_key}\">\n"
            "            <span class=\"swatch\" style=\"background:{color}\"></span>\n"
            "            <span class=\"legend-name\">{name}</span>\n"
            "            <span class=\"legend-count\">{count}</span>\n"
            "          </li>".format(
                kind=html_attr(section.get("kind")),
                section_key=html_attr(section_key),
                color=html_attr(section.get("color")),
                name=escape(str(section.get("name") or "")),
                count=html_attr(count_text),
            )
        )
    return "\n".join(rows)


def build_html(
    event_config: dict[str, Any],
    program: dict[str, Any],
    svg: str,
    sections: list[dict[str, Any]],
    final_seats: list[dict[str, Any]],
    config: dict[str, Any],
) -> str:
    labels = event_config.get("labels") or {}
    header_title = display_title_for_header(event_config, program)
    page_title = f"{header_title} — Friends VIP 座位圖快照"
    meta = f"{labels.get('date', '')}｜{labels.get('venue', '')}".strip("｜")
    note = build_note(sections, final_seats)
    legend = build_legend(sections)
    event_id = str(event_config["eventId"])
    public_seatmap_url = f"https://api.opusformosa.org/public-seatmap/{event_id}"
    defaults = config["displayDefaults"]
    taken_mark_stroke = defaults.get("takenMarkStroke") or "#2f2417"
    stroke_by_kind = {
        "vip-reserved": defaults["vipStroke"],
        "public": defaults["publicStroke"],
        "reserved": defaults["reservedStroke"],
    }
    return f"""<!DOCTYPE html>
<html lang="zh-TW">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="robots" content="noindex,nofollow" />
    <title>{escape(page_title)}</title>
    <style>
      * {{ box-sizing: border-box; }}
      html, body {{ margin: 0; min-height: 100%; background: #eeece7; color: #201f1d; }}
      body {{ font-family: "Noto Serif TC", "PingFang TC", "Microsoft JhengHei", serif; }}
      .page {{ min-height: 100vh; display: grid; grid-template-rows: auto 1fr; }}
      header {{ background: #fbfaf7; border-bottom: 2px solid rgba(66, 198, 187, 0.72); padding: 18px clamp(16px, 3vw, 34px); }}
      .eyebrow {{ margin: 0 0 6px; color: #77716a; font-size: 12px; letter-spacing: 0.18em; text-transform: uppercase; }}
      h1 {{ margin: 0; color: #4b45a0; font-size: clamp(22px, 2.7vw, 34px); line-height: 1.22; letter-spacing: 0.02em; }}
      .meta {{ margin: 7px 0 0; color: #4b45a0; font-size: 15px; font-weight: 700; }}
      .note {{ margin: 8px 0 0; max-width: 980px; color: #5f5b55; font-size: 14px; line-height: 1.8; }}
      main {{ display: grid; grid-template-columns: minmax(0, 1fr) 260px; min-height: 0; }}
      .map-wrap {{ overflow: hidden; padding: clamp(14px, 2.4vw, 28px); background: #f7f5f0; cursor: grab; overscroll-behavior: contain; touch-action: none; user-select: none; }}
      .map-wrap.is-dragging {{ cursor: grabbing; }}
      .map-wrap.is-dragging circle.seat {{ cursor: grabbing; }}
      .map-inner {{ width: max(960px, 150%); max-width: none; margin: 0; transform: translate3d(var(--pan-x, 0px), var(--pan-y, 0px), 0) scale(var(--zoom, 1)); transform-origin: 0 0; will-change: transform; }}
      svg {{ display: block; width: 100%; height: auto; }}
      circle.seat {{ cursor: help; transition: opacity .16s ease, stroke-width .16s ease; }}
      circle.seat:hover, circle.seat.is-active {{ opacity: .72; stroke-width: 3; }}
      line.seat-taken-mark {{ pointer-events: none; }}
      text.seat {{ pointer-events: none; }}
      aside {{ background: #fbfaf7; border-left: 1px solid rgba(75, 69, 160, 0.16); padding: 22px 18px; overflow: auto; }}
      h2 {{ margin: 0 0 14px; color: #4b45a0; font-size: 18px; }}
      .legend {{ list-style: none; margin: 0; padding: 0; display: grid; gap: 10px; }}
      .legend-item {{ display: grid; grid-template-columns: 16px 1fr auto; align-items: center; gap: 9px; font-size: 13px; line-height: 1.45; color: #383531; }}
      .swatch {{ width: 14px; height: 14px; border-radius: 50%; border: 1px solid rgba(0,0,0,.28); }}
      .legend-item[data-kind="vip-reserved"] .swatch {{ box-shadow: inset 0 0 0 2px #5c420d; }}
      .legend-count {{ color: #77716a; font-size: 12px; white-space: nowrap; }}
      .panel {{ margin-top: 20px; padding-top: 16px; border-top: 1px solid rgba(66, 198, 187, 0.58); color: #5f5b55; font-size: 13px; line-height: 1.8; }}
      .panel strong {{ color: #201f1d; }}
      .tip {{ position: fixed; left: 0; top: 0; z-index: 20; display: none; max-width: 280px; padding: 10px 12px; border-radius: 8px; background: rgba(32, 31, 29, .94); color: #fff; font-size: 13px; line-height: 1.65; pointer-events: none; box-shadow: 0 16px 36px rgba(32,31,29,.22); }}
      .tip strong {{ color: #FAAE17; }}
      .tip .taken {{ color: #ffd27a; font-weight: 700; }}
      @media (min-width: 901px) {{
        .page {{ height: 100vh; overflow: hidden; }}
        main {{ overflow: hidden; }}
      }}
      @media (max-width: 900px) {{
        main {{ grid-template-columns: 1fr; }}
        .map-wrap {{ height: 68vh; min-height: 420px; }}
        aside {{ border-left: 0; border-top: 1px solid rgba(75, 69, 160, 0.16); }}
      }}
      @media print {{
        body {{ background: white; }}
        header, aside {{ display: none; }}
        main {{ display: block; }}
        .map-wrap {{ padding: 0; background: white; overflow: visible; }}
        .map-inner {{ min-width: 0; max-width: none; }}
      }}
    </style>
  </head>
  <body>
    <div class="page">
      <header>
        <p class="eyebrow">Friends of Opus Formosa seat map</p>
        <h1>{escape(header_title)}</h1>
        <p class="meta">{escape(meta)}</p>
        <p class="note">{escape(note)}</p>
      </header>
      <main>
        <section class="map-wrap" aria-label="座位圖">
          <div class="map-inner">
{svg}
          </div>
        </section>
        <aside>
          <h2>票區標示</h2>
          <ul class="legend">
{legend}
          </ul>
          <div class="panel">
            <p><strong>使用方式：</strong>拖曳座位圖可移動視角，使用滑鼠滾輪可縮放；點擊或移到座位上可查看座席、票區與票價，再點同一座位可關閉。座位若有叉叉，表示已預訂。申請時請提供場次、張數與座位偏好，團隊會再確認實際可安排席位。</p>
          </div>
        </aside>
      </main>
      <div class="tip" id="tip"></div>
    </div>
    <script>
      const tip = document.getElementById('tip');
      const mapWrap = document.querySelector('.map-wrap');
      const mapInner = document.querySelector('.map-inner');
      const seats = document.querySelectorAll('circle.seat[data-seat-id]');
      let dragState = null;
      let panX = 0;
      let panY = 0;
      let zoom = 1;
      let activeSeat = null;
      let tipPinned = false;
      let suppressSeatClick = false;
      const dragThreshold = 6;
      const minZoom = 0.65;
      const maxZoom = 3.5;
      const formatPrice = (value) => value ? 'NT$' + Number(value).toLocaleString('zh-TW') : '未公開定價';
      const publicSeatmapUrl = {json.dumps(public_seatmap_url, ensure_ascii=False)};
      const svgNamespace = 'http://www.w3.org/2000/svg';
      const takenMarkStroke = {json.dumps(taken_mark_stroke, ensure_ascii=False)};
      const strokeByKind = {json.dumps(stroke_by_kind, ensure_ascii=False)};
      const strokeWidthByKind = {{ 'vip-reserved': '2', public: '1', reserved: '1' }};
      const seatBySvgId = new Map();
      const seatByIdentity = new Map();

      function seatIdentity(floor, row, number) {{
        return [floor || '', row || '', number || ''].join('|');
      }}

      function sectionKeyForSeat(seat) {{
        return [
          seat.dataset.kind || '',
          seat.dataset.sectionName || '',
          seat.getAttribute('fill') || '',
        ].join('|');
      }}

      function slugKind(value) {{
        return String(value || 'seat').toLowerCase().replace(/[^a-z0-9_-]+/g, '-').replace(/^-+|-+$/g, '') || 'seat';
      }}

      function setSeatKindClass(seat, kind) {{
        Array.from(seat.classList).forEach((name) => {{
          if (name.startsWith('seat-') && name !== 'seat' && name !== 'seat-taken') seat.classList.remove(name);
        }});
        seat.classList.add('seat-' + slugKind(kind));
      }}

      function removeTakenMarks(seatId) {{
        document.querySelectorAll('line.seat-taken-mark').forEach((line) => {{
          if (line.dataset.seatId === seatId) line.remove();
        }});
      }}

      function svgNumber(value) {{
        if (!Number.isFinite(value)) return '0';
        if (Number.isInteger(value)) return String(value);
        return value.toFixed(3).replace(/0+$/, '').replace(/\\.$/, '');
      }}

      function createTakenLine(seat, x1, y1, x2, y2, strokeWidth) {{
        const line = document.createElementNS(svgNamespace, 'line');
        line.classList.add('seat-taken-mark');
        line.dataset.seatId = seat.dataset.seatId || '';
        line.setAttribute('x1', svgNumber(x1));
        line.setAttribute('y1', svgNumber(y1));
        line.setAttribute('x2', svgNumber(x2));
        line.setAttribute('y2', svgNumber(y2));
        const transform = seat.getAttribute('transform');
        if (transform) line.setAttribute('transform', transform);
        line.setAttribute('stroke', takenMarkStroke);
        line.setAttribute('stroke-width', svgNumber(strokeWidth));
        line.setAttribute('stroke-linecap', 'round');
        line.setAttribute('opacity', '0.92');
        line.setAttribute('pointer-events', 'none');
        return line;
      }}

      function addTakenMarks(seat) {{
        const cx = Number(seat.getAttribute('cx'));
        const cy = Number(seat.getAttribute('cy'));
        const radius = Number(seat.getAttribute('r'));
        if (!Number.isFinite(cx) || !Number.isFinite(cy) || !Number.isFinite(radius)) return;
        const delta = radius * 0.78;
        const strokeWidth = Math.max(2.2, radius * 0.28);
        const lineA = createTakenLine(seat, cx - delta, cy - delta, cx + delta, cy + delta, strokeWidth);
        const lineB = createTakenLine(seat, cx - delta, cy + delta, cx + delta, cy - delta, strokeWidth);
        const next = seat.nextSibling;
        seat.parentNode.insertBefore(lineA, next);
        seat.parentNode.insertBefore(lineB, next);
      }}

      function setTakenState(seat, taken, label) {{
        removeTakenMarks(seat.dataset.seatId || '');
        if (taken) {{
          seat.classList.add('seat-taken');
          seat.dataset.taken = 'true';
          seat.dataset.availability = 'taken';
          seat.dataset.takenLabel = label || '已預訂';
          seat.dataset.takenSource = 'opus-public-seatmap-api';
          addTakenMarks(seat);
          return;
        }}
        seat.classList.remove('seat-taken');
        delete seat.dataset.taken;
        seat.dataset.availability = 'available';
        delete seat.dataset.takenLabel;
        delete seat.dataset.takenSource;
      }}

      function refreshLegendCounts() {{
        const counts = new Map();
        seats.forEach((seat) => {{
          const key = sectionKeyForSeat(seat);
          const current = counts.get(key) || {{ total: 0, taken: 0 }};
          current.total += 1;
          if (seat.dataset.taken === 'true') current.taken += 1;
          counts.set(key, current);
        }});
        document.querySelectorAll('.legend-item[data-section-key]').forEach((item) => {{
          const count = counts.get(item.dataset.sectionKey);
          const label = item.querySelector('.legend-count');
          if (!count || !label) return;
          label.textContent = count.taken ? count.total + ' 席／已預訂 ' + count.taken + ' 席' : count.total + ' 席';
        }});
      }}

      function updateSeatFromPublicApi(apiSeat) {{
        const seat = seatBySvgId.get(apiSeat.svgId) || seatByIdentity.get(seatIdentity(apiSeat.floorId, apiSeat.rowId, apiSeat.number));
        if (!seat) return false;
        if (apiSeat.floorId != null) seat.dataset.floor = apiSeat.floorId;
        if (apiSeat.rowId != null) seat.dataset.row = apiSeat.rowId;
        if (apiSeat.number != null) seat.dataset.number = apiSeat.number;
        if (apiSeat.sectionId != null) seat.dataset.sectionId = apiSeat.sectionId;
        if (apiSeat.sectionName != null) seat.dataset.sectionName = apiSeat.sectionName;
        if (apiSeat.price != null) seat.dataset.price = apiSeat.price;
        if (apiSeat.color) seat.setAttribute('fill', apiSeat.color);

        const kind = apiSeat.kind || seat.dataset.kind || 'public';
        seat.dataset.kind = kind;
        setSeatKindClass(seat, kind);
        seat.setAttribute('stroke', strokeByKind[kind] || strokeByKind.reserved || '#333333');
        seat.setAttribute('stroke-width', strokeWidthByKind[kind] || '1');
        setTakenState(seat, Boolean(apiSeat.taken) || apiSeat.availability === 'taken', apiSeat.label);
        return true;
      }}

      async function syncPublicSeatmap() {{
        try {{
          const response = await fetch(publicSeatmapUrl, {{ cache: 'no-store', headers: {{ accept: 'application/json' }} }});
          if (!response.ok) throw new Error('HTTP ' + response.status);
          const payload = await response.json();
          if (!payload || !Array.isArray(payload.seats)) throw new Error('Invalid public seatmap payload');
          let applied = 0;
          payload.seats.forEach((apiSeat) => {{
            if (updateSeatFromPublicApi(apiSeat)) applied += 1;
          }});
          refreshLegendCounts();
          if (activeSeat) setTipContent(activeSeat);
          console.info('[seatmap] synced public seat status for ' + applied + ' seats.');
        }} catch (error) {{
          console.warn('[seatmap] public seat status sync failed; using generated snapshot.', error);
        }}
      }}

      function normalizeSvgViewBox() {{
        const svg = mapInner.querySelector('svg');
        if (!svg || svg.hasAttribute('viewBox')) return;
        const bounds = svg.getBBox();
        const pad = 48;
        if (!Number.isFinite(bounds.x) || !Number.isFinite(bounds.y) || bounds.width <= 0 || bounds.height <= 0) return;
        svg.setAttribute('viewBox', [
          bounds.x - pad,
          bounds.y - pad,
          bounds.width + pad * 2,
          bounds.height + pad * 2,
        ].join(' '));
        svg.removeAttribute('width');
        svg.removeAttribute('height');
        svg.setAttribute('preserveAspectRatio', 'xMidYMid meet');
      }}

      function setPan(x, y) {{
        panX = x;
        panY = y;
        mapInner.style.setProperty('--pan-x', panX + 'px');
        mapInner.style.setProperty('--pan-y', panY + 'px');
      }}

      function zoomAt(clientX, clientY, nextZoom) {{
        const clampedZoom = Math.min(maxZoom, Math.max(minZoom, nextZoom));
        if (clampedZoom === zoom) return;
        const wrapRect = mapWrap.getBoundingClientRect();
        const pointerX = clientX - wrapRect.left;
        const pointerY = clientY - wrapRect.top;
        const mapX = (pointerX - panX) / zoom;
        const mapY = (pointerY - panY) / zoom;
        zoom = clampedZoom;
        mapInner.style.setProperty('--zoom', zoom);
        setPan(pointerX - mapX * zoom, pointerY - mapY * zoom);
      }}

      function handleWheel(event) {{
        event.preventDefault();
        const delta = event.deltaMode === 1
          ? event.deltaY * 16
          : event.deltaMode === 2
            ? event.deltaY * mapWrap.clientHeight
            : event.deltaY;
        zoomAt(event.clientX, event.clientY, zoom * Math.exp(-delta * 0.0015));
        clearTip();
      }}

      function setActiveSeat(seat) {{
        document.querySelectorAll('circle.seat.is-active').forEach((item) => {{
          if (item !== seat) item.classList.remove('is-active');
        }});
        if (seat) seat.classList.add('is-active');
        activeSeat = seat || null;
      }}

      function setTipContent(seat) {{
        const taken = seat.dataset.taken === 'true'
          ? '<br><span class="taken">' + (seat.dataset.takenLabel || '已預訂') + '</span>'
          : '';
        tip.innerHTML = '<strong>' + seat.dataset.sectionName + '</strong><br>' +
          seat.dataset.floor + ' 第 ' + seat.dataset.row + ' 排 ' + seat.dataset.number + ' 號<br>' +
          formatPrice(seat.dataset.price) + taken;
      }}

      function positionTip(clientX, clientY) {{
        const pad = 14;
        tip.style.display = 'block';
        const rect = tip.getBoundingClientRect();
        let x = clientX + pad;
        let y = clientY + pad;
        if (x + rect.width > window.innerWidth - pad) x = clientX - rect.width - pad;
        if (y + rect.height > window.innerHeight - pad) y = clientY - rect.height - pad;
        tip.style.transform = 'translate(' + Math.max(pad, x) + 'px,' + Math.max(pad, y) + 'px)';
      }}

      function showTipForSeat(seat, clientX, clientY, pinned) {{
        if (dragState) return;
        tipPinned = Boolean(pinned);
        setActiveSeat(seat);
        setTipContent(seat);
        positionTip(clientX, clientY);
      }}

      function showHoverTip(event) {{
        if (tipPinned) return;
        showTipForSeat(event.currentTarget, event.clientX, event.clientY, false);
      }}

      function moveTip(event) {{
        if (dragState || tipPinned || tip.style.display === 'none') return;
        positionTip(event.clientX, event.clientY);
      }}

      function hideHoverTip(event) {{
        if (tipPinned) return;
        if (activeSeat === event.currentTarget) clearTip();
      }}

      function showFocusTip(event) {{
        if (tipPinned) return;
        const rect = event.currentTarget.getBoundingClientRect();
        showTipForSeat(event.currentTarget, rect.left + rect.width / 2, rect.top + rect.height / 2, false);
      }}

      function hideFocusTip(event) {{
        if (tipPinned) return;
        if (activeSeat === event.currentTarget) clearTip();
      }}

      function toggleSeatTip(event) {{
        event.stopPropagation();
        if (suppressSeatClick) {{
          suppressSeatClick = false;
          return;
        }}
        const seat = event.currentTarget;
        if (tipPinned && activeSeat === seat) {{
          clearTip();
          return;
        }}
        showTipForSeat(seat, event.clientX, event.clientY, true);
      }}

      function clearTip() {{
        tipPinned = false;
        activeSeat = null;
        tip.style.display = 'none';
        document.querySelectorAll('circle.seat.is-active').forEach((seat) => {{
          seat.classList.remove('is-active');
        }});
      }}

      seats.forEach((seat) => {{
        if (seat.dataset.seatId) seatBySvgId.set(seat.dataset.seatId, seat);
        seatByIdentity.set(seatIdentity(seat.dataset.floor, seat.dataset.row, seat.dataset.number), seat);
        seat.addEventListener('mouseenter', showHoverTip);
        seat.addEventListener('mousemove', moveTip);
        seat.addEventListener('mouseleave', hideHoverTip);
        seat.addEventListener('click', toggleSeatTip);
        seat.addEventListener('focus', showFocusTip);
        seat.addEventListener('blur', hideFocusTip);
        seat.setAttribute('tabindex', '0');
      }});

      normalizeSvgViewBox();
      syncPublicSeatmap();

      function markDragIfNeeded(event) {{
        if (!dragState) return;
        const distance = Math.hypot(event.clientX - dragState.startX, event.clientY - dragState.startY);
        if (distance > dragThreshold) dragState.hasMoved = true;
      }}

      function finishPan(event) {{
        const wasMoved = dragState && dragState.hasMoved;
        dragState = null;
        mapWrap.classList.remove('is-dragging');
        if (wasMoved) {{
          suppressSeatClick = true;
          window.setTimeout(() => {{
            suppressSeatClick = false;
          }}, 0);
        }}
      }}

      function beginPan(event) {{
        if (event.button !== undefined && event.button !== 0) return;
        dragState = {{
          pointerId: event.pointerId,
          startX: event.clientX,
          startY: event.clientY,
          panX,
          panY,
          hasMoved: false,
        }};
        mapWrap.classList.add('is-dragging');
        mapWrap.setPointerCapture(event.pointerId);
      }}

      function movePan(event) {{
        if (!dragState || dragState.pointerId !== event.pointerId) return;
        markDragIfNeeded(event);
        setPan(dragState.panX + event.clientX - dragState.startX, dragState.panY + event.clientY - dragState.startY);
        event.preventDefault();
        if (dragState.hasMoved) clearTip();
      }}

      function endPan(event) {{
        if (!dragState || dragState.pointerId !== event.pointerId) return;
        finishPan(event);
      }}

      function centerVipArea() {{
        const vipSeats = Array.from(document.querySelectorAll('circle.seat-vip-reserved'));
        if (!vipSeats.length) return;
        const wrapRect = mapWrap.getBoundingClientRect();
        const bounds = vipSeats.reduce(
          (box, seat) => {{
            const rect = seat.getBoundingClientRect();
            return {{
              left: Math.min(box.left, rect.left),
              right: Math.max(box.right, rect.right),
              top: Math.min(box.top, rect.top),
              bottom: Math.max(box.bottom, rect.bottom),
            }};
          }},
          {{ left: Infinity, right: -Infinity, top: Infinity, bottom: -Infinity }}
        );
        const centerX = (bounds.left + bounds.right) / 2;
        const centerY = (bounds.top + bounds.bottom) / 2;
        setPan(panX + wrapRect.left + wrapRect.width / 2 - centerX, panY + wrapRect.top + wrapRect.height * 0.42 - centerY);
      }}

      mapWrap.addEventListener('click', (event) => {{
        if (!event.target.closest('circle.seat[data-seat-id]')) clearTip();
      }});
      mapWrap.addEventListener('pointerdown', beginPan);
      mapWrap.addEventListener('pointermove', movePan);
      mapWrap.addEventListener('pointerup', endPan);
      mapWrap.addEventListener('pointercancel', endPan);
      mapWrap.addEventListener('lostpointercapture', endPan);
      mapWrap.addEventListener('wheel', handleWheel, {{ passive: false }});
      window.addEventListener('load', () => requestAnimationFrame(centerVipArea));
      window.addEventListener('resize', () => requestAnimationFrame(centerVipArea));
      setTimeout(centerVipArea, 200);
    </script>
  </body>
</html>
"""


def build_snapshot(
    event_config: dict[str, Any],
    program: dict[str, Any],
    event: dict[str, Any],
    sections: list[dict[str, Any]],
    seats: list[dict[str, Any]],
    seat_svg_url: str,
) -> dict[str, Any]:
    labels = event_config.get("labels") or {}
    return {
        "programId": event_config["programId"],
        "eventId": event_config["eventId"],
        "source": {
            "publicEventUrl": public_event_url(event_config["programId"]),
            "seatSvgUrl": seat_svg_url,
            "capturedFrom": "OPENTIX admin seat-map data snapshot.",
        },
        "program": {
            "name": program.get("name"),
            "enUsName": program.get("enUsName"),
            "displayTitle": display_title_for_header(event_config, program),
            "dateLabel": labels.get("date"),
            "venueLabel": labels.get("venue"),
            "startDateTime": event.get("startDateTime"),
            "endDateTime": event.get("endDateTime"),
        },
        "event": {
            "startDateTime": event.get("startDateTime"),
            "endDateTime": event.get("endDateTime"),
            "quantity": event.get("quantity"),
            "showSeatings": event.get("showSeatings"),
            "hideSeatsBeforeOnSale": event.get("hideSeatsBeforeOnSale"),
        },
        "generatedAt": datetime.now(TAIPEI).isoformat(timespec="seconds"),
        "notes": [
            "This file is a static seat-map snapshot for Friends of Opus Formosa seat inquiries.",
            "OPENTIX admin data is the source of truth for non-VIP seats. Friends VIP rules override OPENTIX data for matched seats.",
            "Seats with taken=true are Friends VIP seats already held; they keep their VIP styling and display an X marker.",
            "Public seats with OPENTIX status outside configured available statuses are automatically marked taken and crossed out.",
            "Seat availability status is overlaid from the OPENTIX public seats API when available; admin data remains the source for sections, prices, and SVG.",
        ],
        "takenSeatCount": sum(1 for seat in seats if seat.get("taken")),
        "sections": sections,
        "seats": seats,
    }


def refresh_taken_counts_in_sections(sections: list[dict[str, Any]], seats: list[dict[str, Any]]) -> None:
    taken_counts = Counter(seat["sectionId"] for seat in seats if seat.get("taken"))
    for section in sections:
        section_id = section.get("id")
        section.pop("takenSeatCount", None)
        if taken_counts[section_id]:
            section["takenSeatCount"] = taken_counts[section_id]


def append_unique_note(notes: list[Any], note: str) -> list[str]:
    cleaned = [str(item) for item in notes if item is not None]
    if note not in cleaned:
        cleaned.append(note)
    return cleaned


def fallback_program_and_event(event_config: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    labels = event_config.get("labels") or {}
    title = labels.get("title") or "Opus 音樂節"
    return (
        {
            "id": event_config["programId"],
            "name": title,
            "enUsName": None,
        },
        {
            "id": event_config["eventId"],
            "showSeatings": True,
            "hideSeatsBeforeOnSale": False,
        },
    )


def derive_svg_url(seat_meta: dict[str, Any], section_result: dict[str, Any]) -> str:
    seat_svg_url = seat_meta.get("seatSvgUrl") or section_result.get("seatSvgUrl")
    if seat_svg_url:
        return seat_svg_url
    seat_json_url = seat_meta.get("seatJsonUrl") or section_result.get("seatingMapUrl")
    if seat_json_url:
        return seat_json_url.replace("/jsonFile/", "/svgFile/").replace(".json", ".svg")
    raise SyncError("OPENTIX admin response did not contain seatSvgUrl or seatingMapUrl.")


def render_event(event_config: dict[str, Any], config: dict[str, Any], auth: OpentixAuth, dry_run: bool, strict_counts: bool) -> None:
    program_id = event_config["programId"]
    event_id = event_config["eventId"]
    parent_seating_chart_id = str(event_config["parentSeatingChartId"])
    seat_json_url = config["fetch"]["adminSeatJsonUrl"].format(eventId=urllib.parse.quote(event_id))
    section_seats_url = config["fetch"]["adminSectionSeatsUrl"].format(
        eventId=urllib.parse.quote(event_id),
        parentSeatingChartId=urllib.parse.quote(parent_seating_chart_id),
    )

    print(f"[sync] {event_id} {event_config.get('labels', {}).get('date', '')} {event_config.get('labels', {}).get('title', '')}")
    program, event = fallback_program_and_event(event_config)
    output = config["output"]
    snapshot_path = ROOT / output["json"].format(eventId=event_id)
    existing_snapshot = load_json(snapshot_path) if snapshot_path.exists() else None

    seat_meta = unwrap_api_payload(fetch_admin_json(seat_json_url, auth))
    section_result = unwrap_api_payload(fetch_admin_json(section_seats_url, auth))
    if not isinstance(seat_meta, dict) or not isinstance(section_result, dict):
        raise SyncError(f"Unexpected OPENTIX admin response shape for event {event_id}.")
    seat_svg_url = derive_svg_url(seat_meta, section_result)

    raw_seats = extract_seat_entries(section_result)
    normalized_seats = [normalize_seat(item) for item in raw_seats]
    normalized_seats = [seat for seat in normalized_seats if seat["svgId"] and seat["floorId"] and seat["rowId"] and seat["number"]]
    if not normalized_seats:
        raise SyncError(f"Event {event_id} has no usable seats.")
    try:
        public_statuses = fetch_public_seat_statuses(event_config, config)
        updated_count = overlay_public_statuses(normalized_seats, public_statuses)
        if public_statuses:
            print(f"[sync] {event_id}: overlaid public OPENTIX status for {len(public_statuses)} seats ({updated_count} changed from admin status)")
    except SyncError as exc:
        print(f"[warning] {event_id}: public OPENTIX status overlay failed; using admin status ({exc})", file=sys.stderr)

    raw_sections = section_result.get("section") or []
    official_sections: OrderedDict[str, dict[str, Any]] = OrderedDict()
    for raw_section in raw_sections:
        section = section_from_opentix(raw_section)
        if section["id"]:
            official_sections[section["id"]] = section

    final_seats = apply_rules(normalized_seats, official_sections, event_config, config, strict_counts, existing_snapshot)
    sections = build_sections(final_seats, official_sections, event_config, config)

    raw_svg = fetch_text(seat_svg_url)
    annotated_svg = annotate_svg(raw_svg, final_seats, config)
    snapshot = build_snapshot(event_config, program, event, sections, final_seats, seat_svg_url)
    html = build_html(event_config, program, annotated_svg, sections, final_seats, config)

    write_json(ROOT / output["json"].format(eventId=event_id), snapshot, dry_run)
    write_text(ROOT / output["svg"].format(eventId=event_id), annotated_svg, dry_run)
    write_text(ROOT / output["html"].format(eventId=event_id), html, dry_run)
    print(f"[sync] {event_id}: {len(final_seats)} seats, {sum(1 for seat in final_seats if seat.get('kind') == 'vip-reserved')} Friends VIP seats")


def render_event_from_existing_snapshot(
    event_config: dict[str, Any],
    config: dict[str, Any],
    dry_run: bool,
    strict_counts: bool,
    refresh_public_status: bool,
) -> None:
    event_id = event_config["eventId"]
    output = config["output"]
    snapshot_path = ROOT / output["json"].format(eventId=event_id)
    svg_path = ROOT / output["svg"].format(eventId=event_id)
    if not snapshot_path.exists() or not svg_path.exists():
        raise SyncError(f"Existing generated files not found for event {event_id}.")

    print(f"[sync:local] {event_id} {event_config.get('labels', {}).get('date', '')} {event_config.get('labels', {}).get('title', '')}")
    snapshot = load_json(snapshot_path)
    final_seats = copy.deepcopy(snapshot.get("seats") or [])
    if not final_seats:
        raise SyncError(f"Existing snapshot has no seats for event {event_id}.")
    restore_existing_seats_to_original_sections(final_seats, snapshot.get("sections") or [])
    if refresh_public_status:
        public_statuses = fetch_public_seat_statuses(event_config, config)
        updated_count = overlay_public_statuses(final_seats, public_statuses)
        if public_statuses:
            print(f"[sync:local] {event_id}: refreshed public OPENTIX status for {len(public_statuses)} seats ({updated_count} changed)")
    errors = apply_section_overrides_to_existing(final_seats, event_config, config)
    errors.extend(apply_pulled_seat_overrides(final_seats, event_config, config))
    errors.extend(apply_status_overrides(final_seats, event_config, config))
    apply_opentix_availability_markers(final_seats, config)
    if errors and strict_counts:
        raise SyncError("VIP rule count mismatch:\n" + "\n".join(errors))
    for error in errors:
        print(f"[warning] {error}", file=sys.stderr)

    sections = build_sections(final_seats, OrderedDict(), event_config, config)

    raw_svg = svg_path.read_text(encoding="utf-8")
    annotated_svg = annotate_svg(raw_svg, final_seats, config)
    program = snapshot.get("program") or fallback_program_and_event(event_config)[0]
    html = build_html(event_config, program, annotated_svg, sections, final_seats, config)

    snapshot["generatedAt"] = datetime.now(TAIPEI).isoformat(timespec="seconds")
    snapshot["notes"] = append_unique_note(
        snapshot.get("notes") or [],
        "Seats with taken=true are Friends VIP seats already held; they keep their VIP styling and display an X marker.",
    )
    snapshot["notes"] = append_unique_note(
        snapshot.get("notes") or [],
        "Public seats with OPENTIX status outside configured available statuses are automatically marked taken and crossed out.",
    )
    snapshot["notes"] = append_unique_note(
        snapshot.get("notes") or [],
        "Seat availability status is overlaid from the OPENTIX public seats API when available; admin data remains the source for sections, prices, and SVG.",
    )
    snapshot["takenSeatCount"] = sum(1 for seat in final_seats if seat.get("taken"))
    snapshot["sections"] = sections
    snapshot["seats"] = final_seats

    write_json(snapshot_path, snapshot, dry_run)
    write_text(svg_path, annotated_svg, dry_run)
    write_text(ROOT / output["html"].format(eventId=event_id), html, dry_run)
    print(f"[sync:local] {event_id}: {len(final_seats)} seats, {snapshot['takenSeatCount']} taken/unavailable seats")


def selected_events(config: dict[str, Any], filters: list[str]) -> list[dict[str, Any]]:
    events = config.get("events") or []
    if not filters:
        return events
    selected = []
    wanted = set(filters)
    for event in events:
        keys = {event.get("slug"), event.get("eventId"), event.get("programId")}
        if wanted & keys:
            selected.append(event)
    missing = wanted - {key for event in selected for key in (event.get("slug"), event.get("eventId"), event.get("programId"))}
    if missing:
        raise SyncError("Unknown event filter(s): " + ", ".join(sorted(missing)))
    return selected


def validate_config(config: dict[str, Any]) -> None:
    required_top = ("fetch", "output", "displayDefaults", "fallbacks", "events")
    for key in required_top:
        if key not in config:
            raise SyncError(f"Rules file missing {key}.")
    for event in config["events"]:
        for key in ("programId", "eventId", "parentSeatingChartId"):
            if key not in event:
                raise SyncError(f"Event rule missing {key}: {event}")
        for rule in event.get("sectionOverrides") or []:
            if "id" not in rule or "match" not in rule or "display" not in rule:
                raise SyncError(f"Invalid section override in event {event['eventId']}: {rule}")
        for rule in event.get("seatStatusOverrides") or []:
            if "id" not in rule or "match" not in rule or "status" not in rule:
                raise SyncError(f"Invalid seat status override in event {event['eventId']}: {rule}")
    for record in config.get("pulledSeatRecords") or []:
        for key in ("id", "eventId", "seatSelectors", "expectedSeatCount", "display"):
            if key not in record:
                raise SyncError(f"Pulled seat record missing {key}: {record}")
        for selector in record.get("seatSelectors") or []:
            selector_keys = set(selector)
            required_selector_keys = {"floor", "rows", "numbers"}
            if not required_selector_keys.issubset(selector_keys):
                missing = ", ".join(sorted(required_selector_keys - selector_keys))
                raise SyncError(f"Pulled seat record {record['id']} selector must include {missing}.")
            section_keys = {"sectionId", "sectionIds", "sectionName", "sectionNames"}
            if selector_keys & section_keys:
                invalid = ", ".join(sorted(selector_keys & section_keys))
                raise SyncError(f"Pulled seat record {record['id']} selector must not use section-level keys: {invalid}.")
        display = record.get("display") or {}
        if display.get("kind", "vip-reserved") == "vip-reserved" and "name" not in display:
            raise SyncError(f"Pulled seat record display missing name: {record['id']}")
    policy = config.get("opentixAvailabilityMarkers") or {}
    if policy.get("enabled", False):
        if not isinstance(policy.get("availableStatuses"), list) or not policy.get("availableStatuses"):
            raise SyncError("opentixAvailabilityMarkers.availableStatuses must be a non-empty list.")
        if not isinstance(policy.get("appliesToKinds"), list) or not policy.get("appliesToKinds"):
            raise SyncError("opentixAvailabilityMarkers.appliesToKinds must be a non-empty list.")
    overlay_config = config.get("publicSeatStatusOverlay") or {}
    if overlay_config.get("enabled", False) and "publicSeatStatusUrl" not in config.get("fetch", {}):
        raise SyncError("publicSeatStatusOverlay is enabled, but fetch.publicSeatStatusUrl is missing.")
    print(f"[validate] {len(config['events'])} events in rules file.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync OPENTIX static seat-map snapshots for Friends of Opus Formosa.")
    parser.add_argument("--rules", default=str(DEFAULT_RULES), help="Path to opentix-sync-rules.json")
    parser.add_argument("--event", action="append", default=[], help="Limit to one eventId, programId, or slug. May be repeated.")
    parser.add_argument("--dry-run", action="store_true", help="Fetch and render without writing files.")
    parser.add_argument("--from-existing-snapshot", action="store_true", help="Re-render local generated files without fetching OPENTIX.")
    parser.add_argument("--refresh-public-status", action="store_true", help="With --from-existing-snapshot, refresh seat availability status from the public OPENTIX seats API.")
    parser.add_argument("--no-strict-counts", action="store_true", help="Warn instead of failing when expected VIP seat counts do not match.")
    parser.add_argument("--validate-rules", action="store_true", help="Validate the rules file and exit without fetching OPENTIX.")
    args = parser.parse_args()

    try:
        config = load_json(Path(args.rules))
        validate_config(config)
        if args.validate_rules:
            return 0

        events = selected_events(config, args.event)
        if not events:
            raise SyncError("No events selected.")

        if args.from_existing_snapshot:
            for event in events:
                render_event_from_existing_snapshot(copy.deepcopy(event), config, args.dry_run, not args.no_strict_counts, args.refresh_public_status)
        else:
            auth = OpentixAuth(config)
            for event in events:
                render_event(copy.deepcopy(event), config, auth, args.dry_run, not args.no_strict_counts)
        return 0
    except SyncError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
