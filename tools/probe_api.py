#!/usr/bin/env python3
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE = os.environ.get("FCBQ_API_BASE", "").rstrip("/")
CLUB_ID = os.environ.get("FCBQ_CLUB_ID", "16")
TIMEOUT = 20

if not BASE:
    raise SystemExit("Missing FCBQ_API_BASE secret")

CASES = [
    ("Team/getTeamsFromClub", {"clubId": CLUB_ID}),
    ("Team/getTeamsFromClub", {"idClub": CLUB_ID}),
    ("Team/getTeamsFromClub", {"club": CLUB_ID}),
    ("Match/getAllMatchInLiveVisibleWebByTeam", {"clubId": CLUB_ID}),
    ("Match/getAllMatchInLiveVisibleWebByTeam", {"idClub": CLUB_ID}),
]

SAFE_HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "User-Agent": "ab-premia-calendar/1.0",
}


def summarize(body):
    try:
        value = json.loads(body)
    except json.JSONDecodeError:
        return {"type": "non-json", "preview": body[:300]}
    if isinstance(value, list):
        return {"type": "list", "count": len(value), "sample": value[:1]}
    if isinstance(value, dict):
        cleaned = {}
        for key, item in value.items():
            if any(word in key.lower() for word in ("token", "password", "email", "phone", "dni")):
                cleaned[key] = "[redacted]"
            elif isinstance(item, list):
                cleaned[key] = {"count": len(item), "sample": item[:1]}
            else:
                cleaned[key] = item
        return {"type": "object", "data": cleaned}
    return {"type": type(value).__name__, "preview": str(value)[:300]}


def request(method, path, params):
    url = BASE + "/" + path
    data = None
    if method == "GET":
        url += "?" + urllib.parse.urlencode(params)
    else:
        data = json.dumps(params).encode()
    req = urllib.request.Request(url, data=data, headers=SAFE_HEADERS, method=method)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
            body = response.read(1_000_000).decode("utf-8", "replace")
            return {"path": path, "method": method, "params": params,
                    "status": response.status, "response": summarize(body)}
    except urllib.error.HTTPError as error:
        body = error.read(50_000).decode("utf-8", "replace")
        return {"path": path, "method": method, "params": params,
                "status": error.code, "response": summarize(body)}
    except Exception as error:
        return {"path": path, "method": method, "params": params,
                "status": "network-error", "error": type(error).__name__ + ": " + str(error)}


def main():
    results = []
    for path, params in CASES:
        for method in ("GET", "POST"):
            results.append(request(method, path, params))
    json.dump({"club_id": CLUB_ID, "results": results}, sys.stdout, ensure_ascii=False, indent=2)
    print()


if __name__ == "__main__":
    main()
