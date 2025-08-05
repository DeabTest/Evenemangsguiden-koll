#!/usr/bin/env python3
"""
Scrapar alla evenemang via din proxy och avkapslar Netlify-funktionen.

• Anropar /rest-api/Evenemang/events via proxy
• Unwrappar body-fältet om det finns
• Loopar page=0,1,2… med count=250 tills tom lista
• Filtrerar bort Utställningar
• Sparar data/events_ÅÅÅÅ-MM-DD.json
"""
import json
import datetime
import hashlib
import pathlib
import sys
import time
import urllib.parse

import requests

# Din proxy-endpoint (slut med '?url=' så vi bara behöver quote_orig)
PROXY = "https://cozy-cobbler-0ca46b.netlify.app/.netlify/functions/rss-proxy?url="
API_BASE = "https://visiteskilstuna.se/rest-api/Evenemang/events"
PAGE_SIZE = 250  # max poster per sida

def fetch_page(page: int):
    # 1) Bygg ursprungs-URLen
    params = {
        "count": PAGE_SIZE,
        "filters": "{}",     # tomt filter = alla evenemang
        "page": page,
        "query": "",
        "timestamp": int(time.time() * 1000),
    }
    orig = f"{API_BASE}?{urllib.parse.urlencode(params)}"
    # 2) Wrap via proxy
    proxied = PROXY + urllib.parse.quote(orig, safe="")
    # 3) Hämta
    r = requests.get(proxied, headers={"Accept": "application/json"}, timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"API {r.status_code} på page={page}")
    data = r.json()
    # 4) Unwrap om proxyn lagt det i body
    if isinstance(data, dict) and "body" in data:
        try:
            chunk = json.loads(data["body"])
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Ogiltig JSON i proxy-body: {e}")
    else:
        chunk = data
    if not isinstance(chunk, list):
        raise RuntimeError(f"Fel format på API-svar page={page}: förväntade lista")
    return chunk

def normalize(item: dict):
    # Filtrera bort Utställningar
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

    stamp = datetime.date.today().isoformat()
    outdir = pathlib.Path("data"); outdir.mkdir(exist_ok=True)
    path = outdir / f"events_{stamp}.json"
    path.write_text(json.dumps(events, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Fetched {len(events)} events → {path}")

if __name__ == "__main__":
    main()
