#!/usr/bin/env python3
import json
import sys
import urllib.error
import urllib.request

CONFIG_URL = "https://dsmulti-fcbq-public.optimalwayconsulting.com/public/app/config?version=25.10.31&federation=fcbq"
TEAM_ID = "89527"
PLAYOFF_ID = "83687"
TIMEOUT = 20
HEADERS = {"Accept": "application/json", "User-Agent": "Bàsquet Català/25.10.31"}


def get_api_base():
    request = urllib.request.Request(CONFIG_URL, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return json.load(response)["CDN_ESB"].rstrip("/")


def summarize(body):
    try:
        value = json.loads(body)
    except json.JSONDecodeError:
        return {"type": "non-json", "preview": body[:300]}
    if isinstance(value, list):
        return {"type": "list", "count": len(value), "sample": value[:3]}
    if isinstance(value, dict):
        cleaned = {}
        for key, item in value.items():
            if any(word in key.lower() for word in ("token", "password", "email", "phone", "dni")):
                cleaned[key] = "[redacted]"
            elif isinstance(item, list):
                cleaned[key] = {"count": len(item), "sample": item[:3]}
            else:
                cleaned[key] = item
        return {"type": "object", "data": cleaned}
    return {"type": type(value).__name__, "preview": str(value)[:300]}


def call(base, path):
    request = urllib.request.Request(base + "/" + path, headers=HEADERS)
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            body = response.read(1_000_000).decode("utf-8", "replace")
            return {"path": path, "status": response.status, "response": summarize(body)}
    except urllib.error.HTTPError as error:
        body = error.read(50_000).decode("utf-8", "replace")
        return {"path": path, "status": error.code, "response": summarize(body)}
    except Exception as error:
        return {"path": path, "status": "network-error",
                "error": type(error).__name__ + ": " + str(error)}


def main():
    base = get_api_base()
    ids = (TEAM_ID, PLAYOFF_ID)
    paths = []
    for team_id in ids:
        paths.extend([
            f"Match/getMatchTeam/{team_id}",
            f"Match/getByTeamAndMonth/{team_id}/8/2026",
            f"Match/getByTeamAndMonth/{team_id}/08/2026",
            f"Match/getByTeamAndMonth/{team_id}/2026/8",
            f"Match/getByTeamAndMonth/{team_id}/2026/08",
            f"Match/getAllMatchInLiveVisibleWebByTeam/{team_id}",
        ])
    results = [call(base, path) for path in paths]
    json.dump({"api_base": base, "team_id": TEAM_ID, "playoff_id": PLAYOFF_ID,
               "results": results}, sys.stdout, ensure_ascii=False, indent=2)
    print()


if __name__ == "__main__":
    main()
