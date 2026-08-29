#!/usr/bin/env python3
import hashlib
import json
import os
import re
import unicodedata
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
SETTINGS = json.loads((ROOT / "config/settings.json").read_text(encoding="utf-8"))
OUTPUT = ROOT / "docs/calendars"


def fetch_payload():
    url = os.getenv("DATA_URL", "").strip()
    if not url:
        return json.loads((ROOT / "data/matches.json").read_text(encoding="utf-8"))
    request = urllib.request.Request(url, headers={"User-Agent": "ab-premia-calendar/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def normalize_payload(payload):
    """Adapt this function if the official app uses a different JSON shape."""
    if isinstance(payload, dict):
        for key in ("matches", "partits", "games", "data"):
            if isinstance(payload.get(key), list):
                payload = payload[key]
                break
    if not isinstance(payload, list):
        raise ValueError("La fuente debe devolver una lista de partidos")
    required = {"date", "time", "home_team", "away_team"}
    matches = []
    for item in payload:
        if not isinstance(item, dict) or not required.issubset(item):
            continue
        match = dict(item)
        match["id"] = str(match.get("id") or stable_id(match))
        matches.append(match)
    return matches


def fold(value):
    value = unicodedata.normalize("NFKD", str(value))
    return "".join(c for c in value if not unicodedata.combining(c)).upper()


def slugify(value):
    value = fold(value).lower()
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value or "equip"


def stable_id(match):
    raw = "|".join(str(match.get(k, "")) for k in
                   ("date", "time", "home_team", "away_team", "category"))
    return hashlib.sha256(raw.encode()).hexdigest()[:20]


def is_club_team(name, team_id):
    ids = {str(v) for v in SETTINGS.get("club_team_ids", [])}
    if team_id and str(team_id) in ids:
        return True
    folded = fold(name)
    return any(fold(pattern) in folded for pattern in SETTINGS["club_name_patterns"])


def club_sides(match):
    sides = []
    for side in ("home", "away"):
        name = match[f"{side}_team"]
        team_id = match.get(f"{side}_team_id")
        if is_club_team(name, team_id):
            sides.append((str(team_id or slugify(name)), name))
    return sides


def ics_escape(value):
    return str(value or "").replace("\\", "\\\\").replace("\n", "\\n").replace(",", "\\,").replace(";", "\\;")


def ics_event(match, tz):
    start = datetime.strptime(f'{match["date"]} {match["time"]}', "%Y-%m-%d %H:%M").replace(tzinfo=tz)
    end = start + timedelta(minutes=int(match.get("duration_minutes") or SETTINGS["default_duration_minutes"]))
    title = f'{match["home_team"]} – {match["away_team"]}'
    location = ", ".join(v for v in (match.get("venue"), match.get("address")) if v)
    description = " · ".join(v for v in (match.get("category"), match.get("status")) if v)
    uid = f'{match["id"]}@ab-premia-calendar'
    stamp = datetime.now(ZoneInfo("UTC")).strftime("%Y%m%dT%H%M%SZ")
    return [
        "BEGIN:VEVENT",
        f"UID:{ics_escape(uid)}",
        f"DTSTAMP:{stamp}",
        f"DTSTART;TZID={SETTINGS['timezone']}:{start.strftime('%Y%m%dT%H%M%S')}",
        f"DTEND;TZID={SETTINGS['timezone']}:{end.strftime('%Y%m%dT%H%M%S')}",
        f"SUMMARY:{ics_escape(title)}",
        f"LOCATION:{ics_escape(location)}",
        f"DESCRIPTION:{ics_escape(description)}",
        f"STATUS:{'CANCELLED' if fold(match.get('status', '')) in ('CANCELLED', 'SUSPES', 'SUSPENDIDO') else 'CONFIRMED'}",
        "END:VEVENT",
    ]


def write_calendar(team_slug, team_name, matches):
    tz = ZoneInfo(SETTINGS["timezone"])
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//AB Premia Calendar//ES",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{ics_escape(team_name)}",
        f"X-WR-TIMEZONE:{SETTINGS['timezone']}",
        "REFRESH-INTERVAL;VALUE=DURATION:PT1H",
        "X-PUBLISHED-TTL:PT1H",
    ]
    for match in sorted(matches, key=lambda x: (x["date"], x["time"], x["id"])):
        lines.extend(ics_event(match, tz))
    lines.append("END:VCALENDAR")
    (OUTPUT / f"{team_slug}.ics").write_text("\r\n".join(lines) + "\r\n", encoding="utf-8")


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    matches = normalize_payload(fetch_payload())
    teams = defaultdict(lambda: {"name": "", "matches": []})
    for match in matches:
        for team_id, team_name in club_sides(match):
            slug = slugify(team_id)
            teams[slug]["name"] = team_name
            teams[slug]["matches"].append(match)

    for old_file in OUTPUT.glob("*.ics"):
        if old_file.stem not in teams:
            old_file.unlink()

    index = []
    for slug, team in sorted(teams.items(), key=lambda item: fold(item[1]["name"])):
        write_calendar(slug, team["name"], team["matches"])
        index.append({"slug": slug, "name": team["name"], "matches": len(team["matches"])})

    (OUTPUT / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Generados {len(index)} calendarios con {len(matches)} partidos")


if __name__ == "__main__":
    main()
