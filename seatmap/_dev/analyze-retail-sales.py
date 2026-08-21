#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[2]
RULES_PATH = ROOT / "seatmap" / "_dev" / "opentix-sync-rules.json"
TAIPEI = ZoneInfo("Asia/Taipei")


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True, stderr=subprocess.DEVNULL)


def normalize(value: Any) -> str:
    return "" if value is None else str(value).strip()


def is_available_status(value: Any) -> bool:
    return normalize(value).lower() == "0"


def seat_key(seat: dict[str, Any]) -> tuple[str, str, str]:
    return (
        normalize(seat.get("floorId")),
        normalize(seat.get("rowId")),
        normalize(seat.get("number")),
    )


def parse_snapshot_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(TAIPEI)


def natural_key(value: Any) -> tuple[int, Any]:
    text = normalize(value)
    return (0, int(text)) if text.isdigit() else (1, text)


def expand_values(values: list[Any] | None) -> set[str] | None:
    if values is None:
        return None
    expanded: set[str] = set()
    for value in values:
        if isinstance(value, int):
            expanded.add(str(value))
            continue
        text = normalize(value)
        match = re.fullmatch(r"(-?\d+)\s*-\s*(-?\d+)", text)
        if not match:
            expanded.add(text)
            continue
        start, end = (int(part) for part in match.groups())
        step = 1 if end >= start else -1
        for number in range(start, end + step, step):
            expanded.add(str(number))
    return expanded


def selector_matches(selector: dict[str, Any], seat: dict[str, Any]) -> bool:
    if selector.get("floor") is not None and normalize(selector.get("floor")) != normalize(seat.get("floorId")):
        return False
    rows = expand_values(selector.get("rows"))
    if rows is not None and normalize(seat.get("rowId")) not in rows:
        return False
    numbers = expand_values(selector.get("numbers"))
    if numbers is not None and normalize(seat.get("number")) not in numbers:
        return False
    return True


def current_ticket_price(seat: dict[str, Any]) -> int | None:
    section_name = normalize(seat.get("sectionName"))
    youth_match = re.search(r"青年席位\s*(\d+)\s*元", section_name)
    if youth_match:
        return int(youth_match.group(1))

    # Prefer the explicit ticket-section wording when OPENTIX stores an original
    # price in `price` but the current sale price is embedded in the section name.
    section_match = re.search(r"(\d+)\s*元", section_name)
    if section_match:
        return int(section_match.group(1))

    price = seat.get("price")
    try:
        return int(price) if price is not None else None
    except (TypeError, ValueError):
        return None


def compact_numbers(numbers: list[str]) -> str:
    numbers = sorted([normalize(number) for number in numbers], key=natural_key)
    if not numbers:
        return ""
    if not all(number.isdigit() for number in numbers):
        return ", ".join(numbers)

    values = [int(number) for number in numbers]
    ranges: list[tuple[int, int]] = []
    start = previous = values[0]
    for number in values[1:]:
        if number == previous + 1:
            previous = number
            continue
        ranges.append((start, previous))
        start = previous = number
    ranges.append((start, previous))
    return ", ".join(str(start) if start == end else f"{start}-{end}" for start, end in ranges)


def money(value: int | None) -> str:
    return f"NT${value:,}" if value is not None else "NT$?"


def event_label(event: dict[str, Any]) -> str:
    labels = event.get("labels") or {}
    return f"{labels.get('date', '')} {labels.get('title', '')}（{labels.get('venue', '')}）"


def build_internal_selectors(rules: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    selectors: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in rules.get("pulledSeatRecords") or []:
        selectors[normalize(record.get("eventId"))].extend(record.get("seatSelectors") or [])
    for record in rules.get("assignmentRecords") or []:
        selectors[normalize(record.get("eventId"))].extend(record.get("seatSelectors") or [])
    for event in rules.get("events") or []:
        event_id = normalize(event.get("eventId"))
        for rule in event.get("seatStatusOverrides") or []:
            selectors[event_id].extend((rule.get("match") or {}).get("seatSelectors") or [])
        for rule in event.get("sectionOverrides") or []:
            selectors[event_id].extend((rule.get("match") or {}).get("seatSelectors") or [])
    return selectors


def is_internal_seat(event_id: str, seat: dict[str, Any], selectors: dict[str, list[dict[str, Any]]]) -> bool:
    if any(selector_matches(selector, seat) for selector in selectors.get(event_id, [])):
        return True
    if normalize(seat.get("kind")) == "vip-reserved":
        return True
    section_name = normalize(seat.get("sectionName"))
    return any(pattern in section_name for pattern in ("保留", "評鑑席", "館方工作席"))


def load_snapshot(commit: str, event_id: str) -> dict[str, Any]:
    path = f"assets/opentix/{event_id}-seats.json"
    payload = json.loads(git("show", f"{commit}:{path}"))
    return {
        "time": parse_snapshot_time(payload["generatedAt"]),
        "commit": commit,
        "seats": {
            seat_key(seat): seat
            for seat in payload.get("seats") or []
            if all(seat_key(seat))
        },
    }


def fetch_live_statuses(event: dict[str, Any]) -> dict[tuple[str, str, str], dict[str, Any]]:
    event_id = normalize(event["eventId"])
    chart_id = normalize(event["parentSeatingChartId"])
    url = f"https://csm.api.opentix.life/events/{event_id}/seats?parentSeatingChartId={chart_id}"
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "OpusFormosaRetailSalesReport/1.0"},
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        payload = json.loads(response.read().decode("utf-8"))
    seats = payload.get("result", payload.get("data", payload))
    if isinstance(seats, dict) and isinstance(seats.get("seats"), list):
        seats = seats["seats"]
    if not isinstance(seats, list):
        return {}
    return {seat_key(seat): seat for seat in seats if isinstance(seat, dict) and all(seat_key(seat))}


def commit_time(commit: str) -> datetime:
    timestamp = int(git("show", "-s", "--format=%ct", commit).strip())
    return datetime.fromtimestamp(timestamp, TAIPEI)


def parse_time_arg(value: str | None, default: datetime) -> datetime:
    if not value:
        return default
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        value = f"{value}T00:00:00"
    return datetime.fromisoformat(value).replace(tzinfo=TAIPEI)


def price_band(price: int | None) -> str:
    if price is None:
        return "unknown"
    if price <= 999:
        return "under-1000"
    if price <= 1999:
        return "1000-1999"
    if price <= 2800:
        return "2000-2800"
    return "over-2800"


def analyze(start: datetime, end: datetime, include_live: bool) -> dict[str, Any]:
    rules = json.loads(RULES_PATH.read_text(encoding="utf-8"))
    events = [event for event in rules["events"]]
    event_by_id = {normalize(event["eventId"]): event for event in events}
    event_order = [normalize(event["eventId"]) for event in events]
    path_by_event = {event_id: f"assets/opentix/{event_id}-seats.json" for event_id in event_order}
    event_by_path = {path: event_id for event_id, path in path_by_event.items()}
    internal_selectors = build_internal_selectors(rules)

    all_commits = git("rev-list", "--reverse", "HEAD", "--", "assets/opentix").splitlines()
    baseline = None
    after: list[str] = []
    for commit in all_commits:
        time = commit_time(commit)
        if time < start:
            baseline = commit
        elif time <= end:
            after.append(commit)
    if baseline is None:
        raise RuntimeError("Could not find a baseline snapshot commit before the report window.")

    state: dict[str, dict[tuple[str, str, str], dict[str, Any]]] = {}
    state_time: dict[str, datetime] = {}
    for event_id in event_order:
        try:
            snapshot = load_snapshot(baseline, event_id)
        except subprocess.CalledProcessError:
            continue
        state[event_id] = snapshot["seats"]
        state_time[event_id] = snapshot["time"]

    sales: list[dict[str, Any]] = []
    returns: list[dict[str, Any]] = []
    snapshots_seen: Counter[str] = Counter()

    for commit in after:
        changed_paths = [
            path
            for path in git("diff-tree", "--no-commit-id", "--name-only", "-r", commit, "--", "assets/opentix").splitlines()
            if path in event_by_path
        ]
        for path in changed_paths:
            event_id = event_by_path[path]
            try:
                snapshot = load_snapshot(commit, event_id)
            except Exception:
                continue
            snapshots_seen[event_id] += 1
            previous = state.get(event_id)
            current = snapshot["seats"]
            if previous is not None and start <= snapshot["time"] <= end:
                for key in set(previous) & set(current):
                    before = previous[key]
                    after_seat = current[key]
                    if is_internal_seat(event_id, before, internal_selectors) or is_internal_seat(event_id, after_seat, internal_selectors):
                        continue
                    was_available = is_available_status(before.get("status"))
                    is_available = is_available_status(after_seat.get("status"))
                    if was_available and not is_available:
                        sales.append({
                            "eventId": event_id,
                            "time": snapshot["time"],
                            "key": key,
                            "seat": after_seat,
                        })
                    elif not was_available and is_available:
                        returns.append({
                            "eventId": event_id,
                            "time": snapshot["time"],
                            "key": key,
                            "seat": after_seat,
                        })
            state[event_id] = current
            state_time[event_id] = snapshot["time"]

    live_pending: list[dict[str, Any]] = []
    if include_live:
        for event_id, event in event_by_id.items():
            previous = state.get(event_id)
            if not previous:
                continue
            try:
                live = fetch_live_statuses(event)
            except Exception as error:
                print(f"warning: live fetch failed for {event_id}: {error}", file=sys.stderr)
                continue
            for key in set(previous) & set(live):
                before = previous[key]
                live_raw = live[key]
                if is_available_status(before.get("status")) and not is_available_status(live_raw.get("status")):
                    seat = {**before, "status": live_raw.get("status")}
                    if not is_internal_seat(event_id, seat, internal_selectors):
                        live_pending.append({
                            "eventId": event_id,
                            "time": datetime.now(TAIPEI),
                            "key": key,
                            "seat": seat,
                            "previousSnapshotTime": state_time.get(event_id),
                        })

    sale_by_key: dict[tuple[str, tuple[str, str, str]], list[dict[str, Any]]] = defaultdict(list)
    return_by_key: dict[tuple[str, tuple[str, str, str]], list[dict[str, Any]]] = defaultdict(list)
    for sale in sales:
        sale_by_key[(sale["eventId"], sale["key"])].append(sale)
    for returned in returns:
        return_by_key[(returned["eventId"], returned["key"])].append(returned)

    net_sales = []
    for identity, items in sale_by_key.items():
        last_sale = max(items, key=lambda item: item["time"])
        if not any(returned["time"] > last_sale["time"] for returned in return_by_key.get(identity, [])):
            net_sales.append(last_sale)

    return {
        "start": start,
        "end": end,
        "events": event_by_id,
        "eventOrder": event_order,
        "baseline": baseline,
        "baselineTime": commit_time(baseline),
        "snapshotsSeen": snapshots_seen,
        "grossSales": sales,
        "netSales": net_sales,
        "returns": returns,
        "livePending": live_pending,
    }


def sort_sale(report: dict[str, Any], sale: dict[str, Any]) -> tuple[Any, ...]:
    floor, row, number = sale["key"]
    return (
        report["eventOrder"].index(sale["eventId"]),
        sale["time"],
        floor,
        natural_key(row),
        natural_key(number),
    )


def print_report(report: dict[str, Any], details: bool) -> None:
    events = report["events"]
    event_order = report["eventOrder"]
    net_sales = sorted(report["netSales"], key=lambda sale: sort_sale(report, sale))
    gross_sales = sorted(report["grossSales"], key=lambda sale: sort_sale(report, sale))
    returns = sorted(report["returns"], key=lambda sale: sort_sale(report, sale))

    print(f"Window: {report['start'].strftime('%Y-%m-%d %H:%M')} to {report['end'].strftime('%Y-%m-%d %H:%M')} Asia/Taipei")
    print(f"Baseline: {report['baseline'][:7]} at {report['baselineTime'].strftime('%Y-%m-%d %H:%M')}")
    print(f"Gross public sold transitions: {len(gross_sales)}")
    print(f"Net still-sold seats from period: {len(net_sales)}")
    print(f"Returned-to-available transitions: {len(returns)}")
    print(f"Live pending changes after latest snapshot: {len(report['livePending'])}")

    print("\nBy Price Band")
    for source_name, source_items in (("Net", net_sales), ("Gross", gross_sales)):
        counter = Counter(price_band(current_ticket_price(item["seat"])) for item in source_items)
        print(f"{source_name}: " + ", ".join(f"{band}={counter[band]}" for band in ("under-1000", "1000-1999", "2000-2800", "over-2800", "unknown")))

    print("\nNet By Event And Price")
    for event_id in event_order:
        items = [sale for sale in net_sales if sale["eventId"] == event_id]
        if not items:
            continue
        gross_count = sum(1 for sale in gross_sales if sale["eventId"] == event_id)
        print(f"\n{event_label(events[event_id])}: net {len(items)}, gross {gross_count}")
        by_price = Counter(current_ticket_price(item["seat"]) for item in items)
        for price, count in sorted(by_price.items(), key=lambda item: ((item[0] is None), item[0] or 0)):
            print(f"  {money(price)}: {count}")

    print("\nNet By Ticket Section")
    by_section = Counter(
        (
            item["eventId"],
            normalize(item["seat"].get("sectionName")) or "未命名票區",
            current_ticket_price(item["seat"]),
        )
        for item in net_sales
    )
    for (event_id, section, price), count in sorted(by_section.items(), key=lambda item: (-item[1], event_order.index(item[0][0]), item[0][2] or 0, item[0][1])):
        print(f"{count:>3}  {event_label(events[event_id])}  {section}  {money(price)}")

    if report["livePending"]:
        print("\nLive Pending Changes")
        for event_id in event_order:
            items = [item for item in report["livePending"] if item["eventId"] == event_id]
            if not items:
                continue
            previous_time = items[0].get("previousSnapshotTime")
            since = previous_time.strftime("%Y-%m-%d %H:%M") if previous_time else "latest snapshot"
            print(f"{event_label(events[event_id])}: {len(items)} since {since}")
            rows: dict[tuple[str, str, int | None, str], list[str]] = defaultdict(list)
            for item in sorted(items, key=lambda sale: sort_sale(report, sale)):
                floor, row, number = item["key"]
                seat = item["seat"]
                rows[(floor, row, current_ticket_price(seat), normalize(seat.get("sectionName")))].append(number)
            for (floor, row, price, section), numbers in rows.items():
                print(f"  {floor} {row}排 {compact_numbers(numbers)}  {section} {money(price)}")

    if not details:
        return

    print("\nSeat Detail")
    for event_id in event_order:
        items = [sale for sale in net_sales if sale["eventId"] == event_id]
        if not items:
            continue
        print(f"\n## {event_label(events[event_id])}")
        grouped: dict[tuple[str, int | None], list[dict[str, Any]]] = defaultdict(list)
        for item in items:
            seat = item["seat"]
            grouped[(normalize(seat.get("sectionName")) or "未命名票區", current_ticket_price(seat))].append(item)
        for (section, price), section_items in sorted(grouped.items(), key=lambda item: (-len(item[1]), item[0][1] or 0, item[0][0])):
            print(f"- {section} {money(price)}: {len(section_items)}")
            rows: dict[tuple[str, str], list[str]] = defaultdict(list)
            for item in sorted(section_items, key=lambda sale: sort_sale(report, sale)):
                floor, row, number = item["key"]
                rows[(floor, row)].append(number)
            for (floor, row), numbers in rows.items():
                print(f"  {floor} {row}排: {compact_numbers(numbers)}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze OPENTIX public retail sales transitions from seat-map snapshots.")
    parser.add_argument("--days", type=float, default=7, help="Rolling report window in days. Default: 7.")
    parser.add_argument("--since", help="Start time in Asia/Taipei, e.g. 2026-08-14 or 2026-08-14T12:00:00.")
    parser.add_argument("--until", help="End time in Asia/Taipei. Default: now.")
    parser.add_argument("--live", action="store_true", help="Also compare the latest snapshot with the live public OPENTIX API.")
    parser.add_argument("--details", action="store_true", help="Print seat-level grouped detail.")
    args = parser.parse_args()

    default_end = datetime.now(TAIPEI)
    end = parse_time_arg(args.until, default_end)
    start = parse_time_arg(args.since, end - timedelta(days=args.days))
    report = analyze(start, end, include_live=args.live)
    print_report(report, details=args.details)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
