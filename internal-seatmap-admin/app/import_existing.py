from __future__ import annotations

import argparse
import json
import re
import sqlite3
from pathlib import Path
from typing import Any

from .db import connect, init_db


def expand_values(values: list[Any]) -> list[str]:
    expanded: list[str] = []
    for value in values:
        if isinstance(value, int):
            expanded.append(str(value))
            continue
        text = str(value)
        if re.fullmatch(r"\d+-\d+", text):
            start, end = (int(part) for part in text.split("-", 1))
            expanded.extend(str(number) for number in range(min(start, end), max(start, end) + 1))
        else:
            expanded.append(text)
    return expanded


def expand_selectors(record: dict[str, Any]) -> list[tuple[str, str, str, str]]:
    seats: list[tuple[str, str, str, str]] = []
    event_id = record["eventId"]
    for selector in record["seatSelectors"]:
        for row in expand_values(selector["rows"]):
            for number in expand_values(selector["numbers"]):
                seats.append((event_id, selector["floor"], row, number))
    return seats


def status_matches(value: Any, statuses: list[Any]) -> bool:
    normalized = str(value).strip().lower()
    return any(normalized == str(status).strip().lower() for status in statuses)


def is_opentix_publicly_available(seat: dict[str, Any], rules: dict[str, Any]) -> bool:
    raw_status = seat.get("status")
    if raw_status is None or str(raw_status).strip() == "":
        return False
    policy = rules.get("opentixAvailabilityMarkers") or {}
    available_statuses = policy.get("availableStatuses") or [0, "0"]
    return status_matches(raw_status, available_statuses)


def is_internal_controlled_seat(seat: dict[str, Any]) -> bool:
    if seat.get("kind") == "vip-reserved":
        return True
    return seat.get("takenSource") in {"opus-vip-taken-seat-map", "opus-manual-held-seat-map"}


def upsert_event(conn: sqlite3.Connection, event: dict[str, Any], sort_order: int) -> None:
    labels = event.get("labels", {})
    conn.execute(
        """
        INSERT INTO events (
          event_id, program_id, slug, parent_seating_chart_id,
          date_label, title, venue, sort_order, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(event_id) DO UPDATE SET
          program_id = excluded.program_id,
          slug = excluded.slug,
          parent_seating_chart_id = excluded.parent_seating_chart_id,
          date_label = excluded.date_label,
          title = excluded.title,
          venue = excluded.venue,
          sort_order = excluded.sort_order,
          updated_at = CURRENT_TIMESTAMP
        """,
        (
            event["eventId"],
            event.get("programId"),
            event.get("slug"),
            event.get("parentSeatingChartId"),
            labels.get("date"),
            labels.get("title"),
            labels.get("venue"),
            sort_order,
        ),
    )


def upsert_seat(conn: sqlite3.Connection, event_id: str, seat: dict[str, Any]) -> None:
    conn.execute(
        """
        INSERT INTO seats (
          event_id, floor_id, row_id, seat_number, svg_id,
          section_id, section_name, price, kind, color,
          opentix_status, taken, taken_source, r_x, r_y, raw_json, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(event_id, floor_id, row_id, seat_number) DO UPDATE SET
          svg_id = excluded.svg_id,
          section_id = excluded.section_id,
          section_name = excluded.section_name,
          price = excluded.price,
          kind = excluded.kind,
          color = excluded.color,
          opentix_status = excluded.opentix_status,
          taken = excluded.taken,
          taken_source = excluded.taken_source,
          r_x = excluded.r_x,
          r_y = excluded.r_y,
          raw_json = excluded.raw_json,
          updated_at = CURRENT_TIMESTAMP
        """,
        (
            event_id,
            str(seat["floorId"]),
            str(seat["rowId"]),
            str(seat["number"]),
            seat.get("svgId"),
            seat.get("sectionId"),
            seat.get("sectionName"),
            seat.get("price"),
            seat.get("kind"),
            seat.get("color"),
            None if seat.get("status") is None else str(seat.get("status")),
            1 if seat.get("taken") else 0,
            seat.get("takenSource"),
            seat.get("rX"),
            seat.get("rY"),
            json.dumps(seat, ensure_ascii=False),
        ),
    )


def upsert_override(
    conn: sqlite3.Connection,
    key: tuple[str, str, str, str],
    status: str,
    *,
    assignee: str | None = None,
    note: str | None = None,
    source: str,
    source_record_id: str | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO seat_overrides (
          event_id, floor_id, row_id, seat_number,
          admin_status, assignee_name, note, source, source_record_id, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(event_id, floor_id, row_id, seat_number) DO UPDATE SET
          admin_status = excluded.admin_status,
          assignee_name = excluded.assignee_name,
          note = excluded.note,
          source = excluded.source,
          source_record_id = excluded.source_record_id,
          updated_at = CURRENT_TIMESTAMP
        """,
        (*key, status, assignee, note, source, source_record_id),
    )


def import_existing(repo_root: Path, reset: bool = False) -> dict[str, int]:
    init_db()
    rules_path = repo_root / "seatmap" / "_dev" / "opentix-sync-rules.json"
    assets_dir = repo_root / "assets" / "opentix"
    rules = json.loads(rules_path.read_text(encoding="utf-8"))

    counts = {
        "events": 0,
        "seats": 0,
        "overrides": 0,
        "pulled": 0,
        "assignments": 0,
        "publicAvailableSkipped": 0,
        "nonVipSkipped": 0,
        "warnings": 0,
    }

    with connect() as conn:
        if reset:
            conn.execute("DELETE FROM seat_overrides")
            conn.execute("DELETE FROM seats")
            conn.execute("DELETE FROM events")

        for index, event in enumerate(rules["events"], start=1):
            upsert_event(conn, event, index)
            counts["events"] += 1

        valid_keys: set[tuple[str, str, str, str]] = set()
        seats_by_key: dict[tuple[str, str, str, str], dict[str, Any]] = {}
        for seat_file in sorted(assets_dir.glob("*-seats.json")):
            payload = json.loads(seat_file.read_text(encoding="utf-8"))
            event_id = payload["eventId"]
            for seat in payload["seats"]:
                key = (event_id, str(seat["floorId"]), str(seat["rowId"]), str(seat["number"]))
                valid_keys.add(key)
                seats_by_key[key] = seat
                upsert_seat(conn, event_id, seat)
                counts["seats"] += 1

                if seat.get("taken"):
                    status = "public_sold"
                    if seat.get("takenSource") in {"opus-vip-taken-seat-map", "opus-manual-held-seat-map"}:
                        status = "taken"
                    upsert_override(
                        conn,
                        key,
                        status,
                        note=seat.get("takenNote") or seat.get("note"),
                        source=seat.get("takenSource") or "generated-seat-json",
                    )
                    counts["overrides"] += 1
                elif seat.get("kind") == "vip-reserved":
                    upsert_override(
                        conn,
                        key,
                        "vip_available",
                        note=seat.get("note"),
                        source=seat.get("source") or "generated-seat-json",
                    )
                    counts["overrides"] += 1

        for record in rules.get("pulledSeatRecords", []):
            selector_keys = [key for key in expand_selectors(record) if key in valid_keys]
            expected = record.get("expectedSeatCount")
            if expected is not None and expected != len(selector_keys):
                counts["warnings"] += 1
                print(
                    f"warning: {record['id']} expected {expected} seats, imported {len(selector_keys)}",
                    flush=True,
                )
            available_keys = [
                key for key in selector_keys if is_opentix_publicly_available(seats_by_key.get(key, {}), rules)
            ]
            non_vip_keys = [
                key for key in selector_keys
                if key not in available_keys and not is_internal_controlled_seat(seats_by_key.get(key, {}))
            ]
            if available_keys:
                counts["warnings"] += 1
                counts["publicAvailableSkipped"] += len(available_keys)
                print(
                    f"warning: {record['id']} skipped {len(available_keys)} OPENTIX-publicly-available seat(s)",
                    flush=True,
                )
            if non_vip_keys:
                counts["warnings"] += 1
                counts["nonVipSkipped"] += len(non_vip_keys)
                print(
                    f"warning: {record['id']} skipped {len(non_vip_keys)} non-VIP seat(s)",
                    flush=True,
                )
            for key in selector_keys:
                if key in available_keys or key in non_vip_keys:
                    continue
                upsert_override(
                    conn,
                    key,
                    "pulled",
                    note=record.get("label") or record.get("note"),
                    source="pulledSeatRecords",
                    source_record_id=record["id"],
                )
                counts["pulled"] += 1

        for record in rules.get("assignmentRecords", []):
            assignee = record.get("assignee", {}).get("displayName")
            if not assignee:
                continue
            selector_keys = [key for key in expand_selectors(record) if key in valid_keys]
            expected = record.get("expectedSeatCount")
            if expected is not None and expected != len(selector_keys):
                counts["warnings"] += 1
                print(
                    f"warning: {record['id']} expected {expected} seats, imported {len(selector_keys)}",
                    flush=True,
                )
            available_keys = [
                key for key in selector_keys if is_opentix_publicly_available(seats_by_key.get(key, {}), rules)
            ]
            non_vip_keys = [
                key for key in selector_keys
                if key not in available_keys and not is_internal_controlled_seat(seats_by_key.get(key, {}))
            ]
            if available_keys:
                counts["warnings"] += 1
                counts["publicAvailableSkipped"] += len(available_keys)
                print(
                    f"warning: {record['id']} skipped {len(available_keys)} OPENTIX-publicly-available seat(s)",
                    flush=True,
                )
            if non_vip_keys:
                counts["warnings"] += 1
                counts["nonVipSkipped"] += len(non_vip_keys)
                print(
                    f"warning: {record['id']} skipped {len(non_vip_keys)} non-VIP seat(s)",
                    flush=True,
                )
            for key in selector_keys:
                if key in available_keys or key in non_vip_keys:
                    continue
                upsert_override(
                    conn,
                    key,
                    "vip_assigned",
                    assignee=assignee,
                    note=record.get("note"),
                    source="assignmentRecords",
                    source_record_id=record["id"],
                )
                counts["assignments"] += 1

    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Import existing static seatmap data into SQLite.")
    parser.add_argument("--repo-root", default="..", type=Path)
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()
    counts = import_existing(args.repo_root.resolve(), reset=args.reset)
    print(json.dumps(counts, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
