#!/usr/bin/env python3
"""
Scrapar alla evenemang via din proxy för att kringgå CORS.

• Anropar /rest-api/Evenemang/events via proxy-endpoint
• Loopar page=0,1,2… med count=250 tills ingen data kvar
• Filtrerar bort Utställningar
• Sparar data/events_YYYY-MM-DD.json
"""
import json
import datetime
import hashlib
import pathlib
import sys
import time
import urllib.parse
import requests

# Din proxy-URL
PROXY = "https://cozy-cobbler-0ca46b.netlify.app/.netlify/functions/rss-proxy?url="
API_BASE = "https://visiteskilstuna.se/rest-api/Evenemang/events"
PAGE_SIZE = 250

def fetch_page(page: int):
    params = {
        "count": PAGE_SIZE,
        "filters": "{}",
        "page": page,
        "query": "",
        "timestamp": int(time.time() * 1000)
    }
    # Bygg original-URL
    orig = f"{API_BASE}?{urllib.parse.urlencode(params)}"
    # Wrap via proxy
    url = PROXY + urllib.parse.quote(orig, safe='')
    r = requests.get(url, headers={"Accept": "application/json"}, timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"API {r.status_code} på page={page}")
    return r.json()

def normalize(item: dict):
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
        if not isinstance(chunk, list) or not chunk:
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
    outdir = pathlib.Path("data"); outdir.mkdir(exist_ok=True)
    path = outdir / f"events_{today}.json"
    path.write_text(json.dumps(events, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Fetched {len(events)} events → {path}")

if __name__ == "__main__":
    main()
