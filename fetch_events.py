#!/usr/bin/env python3
"""
Hämtar ALLA evenemang via /rest-api/Evenemang/events.

• count=250 så det räcker med två-tre sidor
• filters=%7B%7D (tom objekt) ger både Evenemang & Utställningar
  - vi filtrerar bort Utställningar i Python
• timestamp=epoch-ms krävs – annars svarar API:t ”Hello World”
• Loopar page=0,1,2 … tills listan blir tom
• Sparar data/events_YYYY-MM-DD.json
"""
import json, datetime, pathlib, hashlib, time, requests, sys

BASE = "https://visiteskilstuna.se/rest-api/Evenemang/events"
HEAD = {
    "Accept": "application/json",
    "Referer": "https://evenemang.eskilstuna.se/",
    "User-Agent": "Github-Action/1.0",
}

SIZE = 250         # max poster per sida

def fetch_page(page: int):
    params = {
        "count": SIZE,
        "filters": "{}",       # tomma filter -> allt
        "page": page,
        "query": "",
        "timestamp": int(time.time() * 1000)
    }
    r = requests.get(BASE, params=params, headers=HEAD, timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"API {r.status_code} page={page}")
    return r.json()            # alltid en lista

def normalize(item: dict):
    """Plocka fält & hoppa över Utställningar."""
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
    events, page = [], 0
    while True:
        chunk = fetch_page(page)
        if not chunk:
            break
        for raw in chunk:
            ev = normalize(raw)
            if ev:
                events.append(ev)
        if len(chunk) < SIZE:   # sista sidan
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
    out = pathlib.Path("data"); out.mkdir(exist_ok=True)
    path = out / f"events_{stamp}.json"
    path.write_text(json.dumps(events, ensure_ascii=False, indent=2))
    print(f"Fetched {len(events)} events → {path}")

if __name__ == "__main__":
    main()
