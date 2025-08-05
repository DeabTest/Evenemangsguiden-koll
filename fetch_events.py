#!/usr/bin/env python3
"""
Hämtar alla evenemang via /rest-api/Evenemang/events med count=250.

• Loopar page=0,1,2… tills svaret är tomt
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

PAGE_SIZE = 250  # antal poster per sida

def fetch_page(page: int):
    params = {
        "count": PAGE_SIZE,
        "filters": "{}",            # tomt filter = alla evenemang
        "page": page,
        "query": "",
        "timestamp": int(time.time() * 1000)
    }
    resp = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(f"API {resp.status_code} på page={page}")
    return resp.json()

def normalize(item: dict):
    # Filtrera bort Utställningar om du vill:
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
        "id":   hashlib.sha1(url.encode()).hexdigest()[:12],
        "title": title,
        "date":  date,
        "url":   url,
    }

def fetch_all():
    events = []
    page = 0
    while True:
        chunk = fetch_page(page)
        if not chunk:
            break
        for raw in chunk:
            ev = normalize(raw)
            if ev:
                events.append(ev)
        if len(chunk) < PAGE_SIZE:
            break
        page += 1
    return events

def main():
    try:
        events = fetch_all()
    except Exception as e:
        print("API-fel:", e, file=sys.stderr)
        sys.exit(1)

    today = datetime.date.today().isoformat()
    outdir = pathlib.Path("data")
    outdir.mkdir(exist_ok=True)
    path = outdir / f"events_{today}.json"
    path.write_text(json.dumps(events, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Fetched {len(events)} events → {path}")

if __name__ == "__main__":
    main()
