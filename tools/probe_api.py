#!/usr/bin/env python3
import json
import sys
import urllib.error
import urllib.parse
import urllib.request

CONFIG_URL = "https://dsmulti-fcbq-public.optimalwayconsulting.com/public/app/config?version=25.10.31&federation=fcbq"
CLUB_ID = "16"
TIMEOUT = 20
HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "User-Agent": "Bàsquet Català/25.10.31",
}


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
        return {"type": "list", "count": len(value), "sample": value[:2]}
    if isinstance(value, dict):
        cleaned = {}
        for key, item in value.items():
            if any(word in key.lower() for word in ("token", "password", "email", "phone", "dni")):
                cleaned[key] = "[redacted]"
            elif isinstance(item, list):
                cleaned[key] = {"count": len(item), "sample": item[:2]}
            else:
                cleaned[key] = item
        return {"type": "object", "data": cleaned}
    return {"type": type(value).__name__, "preview": str(value)[:300]}


def call(base, method, path, params):
    url = base + "/" + path
    data = None
    if method == "GET":
        url += "?" + urllib.parse.urlencode(params)
    else:
        data = json.dumps(params).encode()
    request = urllib.request.Request(url, data=data, headers=HEADERS, method=method)
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
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
    base = get_api_base()
    cases = [
        ("Team/getTeamsFromClub", {"clubId": CLUB_ID}),
        ("Team/getTeamsFromClub", {"idClub": CLUB_ID}),
        ("Team/getTeamsFromClub", {"club": CLUB_ID}),
        ("Match/getAllMatchInLiveVisibleWebByClub", {"clubId": CLUB_ID}),
        ("Match/getAllMatchInLiveVisibleWebByClub", {"idClub": CLUB_ID}),
        ("Match/getAllMatchInLiveVisibleWebByClub", {"club": CLUB_ID}),
        ("Match/getMatchClubMonth", {"clubId": CLUB_ID, "month": 8, "year": 2026}),
        ("Match/getMatchClubMonth", {"idClub": CLUB_ID, "month": 8, "year": 2026}),
    ]
    results = []
    for path, params in cases:
        for method in ("GET", "POST"):
            results.append(call(base, method, path, params))
    json.dump({"api_base": base, "club_id": CLUB_ID, "results": results},
              sys.stdout, ensure_ascii=False, indent=2)
    print()


if __name__ == "__main__":
    main()
