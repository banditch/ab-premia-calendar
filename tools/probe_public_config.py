#!/usr/bin/env python3
import json
import urllib.error
import urllib.request

HOST = "https://dsmulti-fcbq-public.optimalwayconsulting.com"
PATHS = [
    "/public/app/config?version=25.10.31&federation=fcbq",
    "/public/app/config?federation=fcbq&version=25.10.31",
    "/public/app/config?version=25.10.31&federation=FCBQ",
    "/public/app/config?version=25.10.31&federation=1",
    "/public/app/config?version=25.10.31",
]


def redact(value, key=""):
    sensitive = ("token", "secret", "password", "authorization", "api_key", "apikey")
    if any(part in key.lower() for part in sensitive):
        if isinstance(value, str):
            return "[redacted string, length=%d]" % len(value)
        return "[redacted]"
    if isinstance(value, dict):
        return {k: redact(v, k) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v, key) for v in value[:3]]
    return value


results = []
for path in PATHS:
    request = urllib.request.Request(
        HOST + path,
        headers={"Accept": "application/json", "User-Agent": "Bàsquet Català/25.10.31"},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            body = response.read(1_000_000).decode("utf-8", "replace")
            try:
                parsed = redact(json.loads(body))
            except json.JSONDecodeError:
                parsed = {"preview": body[:500]}
            results.append({"path": path, "status": response.status, "response": parsed})
    except urllib.error.HTTPError as error:
        body = error.read(50_000).decode("utf-8", "replace")
        results.append({"path": path, "status": error.code, "preview": body[:500]})
    except Exception as error:
        results.append({"path": path, "status": "network-error",
                        "error": type(error).__name__ + ": " + str(error)})

print(json.dumps({"host": HOST, "results": results}, ensure_ascii=False, indent=2))
