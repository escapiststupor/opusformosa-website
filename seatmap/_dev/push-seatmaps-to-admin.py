#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ASSETS_DIR = ROOT / "assets" / "opentix"


def post_event(api_base: str, token: str, seats_path: Path, commit_sha: str) -> dict:
    seats_payload = json.loads(seats_path.read_text(encoding="utf-8"))
    event_id = str(seats_payload.get("eventId") or "").strip()
    if not event_id:
        raise ValueError(f"{seats_path} is missing eventId")

    svg_path = seats_path.with_name(f"{event_id}-seatmap.svg")
    payload = {
        "source": "github-actions",
        "commitSha": commit_sha,
        "seatsPayload": seats_payload,
        "svg": svg_path.read_text(encoding="utf-8") if svg_path.exists() else "",
    }
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        f"{api_base.rstrip('/')}/internal/opentix-sync/events/{event_id}",
        data=body,
        method="POST",
        headers={
            "authorization": f"Bearer {token}",
            "content-type": "application/json; charset=utf-8",
            "user-agent": "opusformosa-seatmap-sync/1.0",
        },
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Push OPENTIX seat snapshots to the internal seatmap admin API.")
    parser.add_argument("--api-base", default=os.environ.get("SEATMAP_ADMIN_SYNC_URL", "https://api.opusformosa.org"))
    parser.add_argument("--token", default=os.environ.get("SEATMAP_ADMIN_SYNC_TOKEN", ""))
    parser.add_argument("--assets-dir", type=Path, default=DEFAULT_ASSETS_DIR)
    parser.add_argument("--commit-sha", default=os.environ.get("GITHUB_SHA", "local"))
    args = parser.parse_args()

    if not args.token:
        print("error: missing SEATMAP_ADMIN_SYNC_TOKEN", file=sys.stderr)
        return 2

    seats_files = sorted(args.assets_dir.glob("*-seats.json"))
    if not seats_files:
        print(f"error: no *-seats.json files found in {args.assets_dir}", file=sys.stderr)
        return 2

    failed = False
    for seats_path in seats_files:
        try:
            result = post_event(args.api_base, args.token, seats_path, args.commit_sha)
            print(
                f"[admin-sync] {result['eventId']}: "
                f"{result['seatCount']} seats, "
                f"{result['preservedInternalOverrides']} internal overrides preserved, "
                f"{result['removedGeneratedOverrides']} generated overrides removed, "
                f"svg={'yes' if result['storedSvg'] else 'no'}"
            )
        except urllib.error.HTTPError as error:
            failed = True
            detail = error.read().decode("utf-8", errors="replace")
            print(f"error: {seats_path.name}: HTTP {error.code}: {detail}", file=sys.stderr)
        except Exception as error:
            failed = True
            print(f"error: {seats_path.name}: {error}", file=sys.stderr)

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
