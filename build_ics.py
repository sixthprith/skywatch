#!/usr/bin/env python3
"""Build feed.ics from the live launch API plus events.json.

Runs in GitHub Actions on a schedule. Subscribe to the published feed.ics in
Google Calendar and your phone handles the notifications.
Standard library only — no pip install step needed.
"""

import json
import pathlib
import re
import urllib.request
from datetime import datetime, timedelta, timezone

ROOT = pathlib.Path(__file__).resolve().parent.parent
API = "https://ll.thespacedevs.com/2.3.0/launches/upcoming/?limit=60"
FLORIDA = re.compile(r"florida|, fl|cape canaveral|kennedy", re.I)


def fetch_launches():
    req = urllib.request.Request(API, headers={"User-Agent": "sky-watch-feed"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)

    out = []
    for launch in data.get("results", []):
        pad = launch.get("pad") or {}
        loc = (pad.get("location") or {}).get("name", "")
        if not FLORIDA.search(loc):
            continue
        try:
            net = datetime.fromisoformat(launch["net"].replace("Z", "+00:00"))
        except (KeyError, ValueError):
            continue
        out.append({
            "uid": f"ll-{launch['id']}@skywatch",
            "summary": launch.get("name", "Launch"),
            "location": f"{pad.get('name', 'Pad')}, {loc}",
            "start": net,
            "end": net + timedelta(hours=1),
            "all_day": False,
            "description": (launch.get("status") or {}).get("name", ""),
        })
    return out


def fetch_curated():
    raw = json.loads((ROOT / "events.json").read_text())
    out = []
    for e in raw.get("events", []):
        start = datetime.fromisoformat(e["start"]).date()
        end = datetime.fromisoformat(e.get("end", e["start"])).date()
        out.append({
            "uid": f"{e['id']}@skywatch",
            "summary": e["name"],
            "location": e.get("venue", ""),
            "start": start,
            "end": end + timedelta(days=1),  # ICS all-day end is exclusive
            "all_day": True,
            "description": e.get("detail", ""),
        })
    return out


def escape(text):
    return (str(text).replace("\\", "\\\\").replace(",", "\\,")
            .replace(";", "\\;").replace("\n", "\\n"))


def to_ics(events):
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Sky Watch//EN",
        "CALSCALE:GREGORIAN", "X-WR-CALNAME:Sky Watch — Florida",
        "X-PUBLISHED-TTL:PT6H",
    ]
    for e in events:
        lines += ["BEGIN:VEVENT", f"UID:{e['uid']}", f"DTSTAMP:{now}"]
        if e["all_day"]:
            lines += [
                f"DTSTART;VALUE=DATE:{e['start'].strftime('%Y%m%d')}",
                f"DTEND;VALUE=DATE:{e['end'].strftime('%Y%m%d')}",
            ]
        else:
            lines += [
                f"DTSTART:{e['start'].astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
                f"DTEND:{e['end'].astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
            ]
        lines += [
            f"SUMMARY:{escape(e['summary'])}",
            f"LOCATION:{escape(e['location'])}",
            f"DESCRIPTION:{escape(e['description'])[:300]}",
            "BEGIN:VALARM", "TRIGGER:-PT3H", "ACTION:DISPLAY",
            "DESCRIPTION:Sky Watch", "END:VALARM",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


def main():
    events = fetch_curated()
    try:
        events += fetch_launches()
    except Exception as err:  # keep the feed alive if the API is down
        print(f"launch feed unavailable, publishing curated events only: {err}")
    (ROOT / "feed.ics").write_text(to_ics(events))
    print(f"wrote feed.ics with {len(events)} events")


if __name__ == "__main__":
    main()
