#!/usr/bin/env python3
import json
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
CONFIG_URL = (
    "https://dsmulti-fcbq-public.optimalwayconsulting.com/public/app/config"
    "?version=25.10.31&federation=fcbq"
)
CLUB_ID = "16"
HEADERS = {"Accept": "application/json", "User-Agent": "Bàsquet Català/25.10.31"}
TEAM_CATALOG = {}


def get_json(url):
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def api_data(base, path):
    payload = get_json(f"{base}/{path}")
    if payload.get("result") != "OK":
        raise RuntimeError(f"API error for {path}: {payload.get('message')}")
    return payload.get("messageData") or []


def team_key(team):
    category = team.get("idCategory") or team.get("idCategoriesRegistred") or "team"
    code = team.get("teamCode") or "00"
    return f"{category}-{code}"


def team_label(team):
    name = team.get("name") or "AB Premià"
    category = team.get("categoriesRegistredName") or ""
    return f"{name} — {category}" if category else name


def normalize_official_match(item):
    match_day = str(item.get("matchDay") or "")
    if len(match_day) < 16:
        return None
    location = ", ".join(
        value for value in (
            item.get("adressField"),
            item.get("postalCodeField"),
            item.get("nameTown"),
        ) if value
    )
    if item.get("idMatchResult"):
        status = "played"
    else:
        status = item.get("publicMessage") or item.get("description") or "scheduled"
    return {
        "id": str(item.get("idMatchCall") or item.get("idMatch") or item.get("matchCallUuid")),
        "date": match_day[:10],
        "time": match_day[11:16],
        "home_team": item.get("nameLocalTeam") or item.get("nameLocalTeamOrganization") or "Local",
        "away_team": item.get("nameVisitorTeam") or item.get("nameVisitorTeamOrganization") or "Visitante",
        "home_team_id": str(item.get("idLocalTeam") or ""),
        "away_team_id": str(item.get("idVisitorTeam") or ""),
        "category": item.get("nameCategorySigned") or item.get("nameCategory") or "",
        "competition": item.get("nameCompetition") or "",
        "venue": item.get("nameField") or "",
        "address": location,
        "status": status,
    }


def fetch_payload():
    config = get_json(CONFIG_URL)
    base = config["CDN_ESB"].rstrip("/")
    teams = api_data(base, f"Team/getTeamsFromClub/{CLUB_ID}")
    for team in teams:
        team_id = str(team["idSignedTeam"])
        TEAM_CATALOG[team_id] = {
            "key": team_key(team),
            "label": team_label(team),
        }

    matches = {}
    for team_id in TEAM_CATALOG:
        for item in api_data(base, f"Match/getMatchTeam/{team_id}"):
            match = normalize_official_match(item)
            if match:
                matches[match["id"]] = match
    return list(matches.values())


def normalize_payload(payload):
    required = {"date", "time", "home_team", "away_team"}
    matches = []
    for item in payload:
        if isinstance(item, dict) and required.issubset(item):
            matches.append(dict(item))
    return matches


def fold(value):
    value = unicodedata.normalize("NFKD", str(value))
    return "".join(c for c in value if not unicodedata.combining(c)).upper()


def slugify(value):
    value = fold(value).lower()
    return re.sub(r"[^a-z0-9]+", "-", value).strip("-") or "equip"


def is_club_team(name, team_id):
    if team_id and str(team_id) in TEAM_CATALOG:
        return True
    folded = fold(name)
    return any(fold(pattern) in folded for pattern in SETTINGS["club_name_patterns"])


def club_sides(match):
    sides = []
    for side in ("home", "away"):
        name = match[f"{side}_team"]
        team_id = str(match.get(f"{side}_team_id") or "")
        if is_club_team(name, team_id):
            catalog = TEAM_CATALOG.get(team_id)
            if catalog:
                sides.append((catalog["key"], catalog["label"]))
            else:
                sides.append((team_id or slugify(name), name))
    return sides


def ics_escape(value):
    return (str(value or "").replace("\\", "\\\\").replace("\n", "\\n")
            .replace(",", "\\,").replace(";", "\\;"))


def ics_event(match, tz):
    start = datetime.strptime(
        f'{match["date"]} {match["time"]}', "%Y-%m-%d %H:%M"
    ).replace(tzinfo=tz)
    end = start + timedelta(
        minutes=int(match.get("duration_minutes") or SETTINGS["default_duration_minutes"])
    )
    title = f'{match["home_team"]} – {match["away_team"]}'
    location = ", ".join(v for v in (match.get("venue"), match.get("address")) if v)
    description = " · ".join(
        v for v in (match.get("category"), match.get("competition"), match.get("status")) if v
    )
    uid = f'{match["id"]}@ab-premia-calendar'
    stamp = datetime.now(ZoneInfo("UTC")).strftime("%Y%m%dT%H%M%SZ")
    cancelled_words = ("CANCELLED", "CANCELADO", "SUSPES", "SUSPÈS", "SUSPENDIDO")
    cancelled = any(word in fold(match.get("status", "")) for word in cancelled_words)
    return [
        "BEGIN:VEVENT",
        f"UID:{ics_escape(uid)}",
        f"DTSTAMP:{stamp}",
        f"DTSTART;TZID={SETTINGS['timezone']}:{start.strftime('%Y%m%dT%H%M%S')}",
        f"DTEND;TZID={SETTINGS['timezone']}:{end.strftime('%Y%m%dT%H%M%S')}",
        f"SUMMARY:{ics_escape(title)}",
        f"LOCATION:{ics_escape(location)}",
        f"DESCRIPTION:{ics_escape(description)}",
        f"STATUS:{'CANCELLED' if cancelled else 'CONFIRMED'}",
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
    (OUTPUT / f"{team_slug}.ics").write_text(
        "\r\n".join(lines) + "\r\n", encoding="utf-8"
    )


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    matches = normalize_payload(fetch_payload())
    teams = defaultdict(lambda: {"name": "", "matches": []})

    for entry in TEAM_CATALOG.values():
        slug = slugify(entry["key"])
        teams[slug]["name"] = entry["label"]

    for match in matches:
        for team_key_value, team_name in club_sides(match):
            slug = slugify(team_key_value)
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
    print(f"Generated {len(index)} calendars with {len(matches)} unique matches")


if __name__ == "__main__":
    main()
