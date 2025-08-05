#!/usr/bin/env python3
"""
Hämtar alla evenemang via /rest-api/Evenemang/events

• Börjar på page=0
• count=250 (max per sida)
• Loopar sida för sida tills listan blir tom
• Sparar data/events_YYYY-MM-DD.json
"""
import json
import datetime
import pathlib
import hashlib
import requests
import time
import sys

BASE_URL = "https://visiteskilstuna.se/rest-api/Evenemang/events"
HEADERS = {
    "Accept": "application/json",
    "Referer": "https://evenemang.eskilstuna.se",
    "User-Agent": "GitHub-Action/1.0",
}

PAGE_SIZE = 250  # Max antal poster per sida

def fetch_page(page: int):
    params = {
        "count": PAGE_SIZE,
        "filters": "{}",           # tomt filter = alla evenemang
        "page": page,
        "query": "",
        "timestamp": int(time.time() * 1000),
    }
    r = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"API {r.status_code} på page={page}")
    return r.json()  # förväntat: lista med event-objekt

def normalize(item: dict):
    """Plocka ut de fält vi vill ha & hoppa över Utställningar."""
    if item.get("categoryName") == "Utställningar":
        return None
    title = item.get("title") or item.get("name") or ""
    if not title:
        return None
    url = item.get("presentationUrl") or item.get("url") or ""
    if url and not url.startswith("http"):
        url = "https://visiteskilstuna.se" + url
    date = (item.get("startDate") or item.get("date") or "")[:10]
    return {
        "id": hashlib.sha1(url.encode()).hexdigest()[:12],
        "title": title,
        "date": date,
        "url": url,
    }

def fetch_all():
    events = []
    page = 0
    while True:
        chunk = fetch_page(page)
        if not chunk:  # tom lista → klart
            break
        for raw in chunk:
            ev = normalize(raw)
            if ev:
                events.append(ev)
        if len(chunk) < PAGE_SIZE:
            break  # sista sidan
        page += 1
    return events

def main():
    try:
        events = fetch_all()
    except Exception as e:
        print("API-fel:", e, file=sys.stderr)
        sys.exit(1)

    stamp = datetime.date.today().isoformat()
    out = pathlib.Path("data"); out.mkdir(exist_ok=True)
    path = out / f"events_{stamp}.json"
    path.write_text(json.dumps(events, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Fetched {len(events)} events → {path}")

if __name__ == "__main__":
    main()
