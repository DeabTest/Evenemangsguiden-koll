#!/usr/bin/env python3
"""
Hämtar alla evenemang via SiteVisions REST-API istället för att skrapa UI.

• Loopar page=0,1,2 … tills svaret är tomt
• page-storlek 250 → oftast bara två anrop
• Titeln, datum och länk plockas direkt ur JSON
• Sparar data/events_YYYY-MM-DD.json
"""
import json, datetime, pathlib, hashlib, sys, requests

API = "https://visiteskilstuna.se/rest-api/Evenemang"
HEADERS = {
    "Accept": "application/json",
    "Referer": "https://evenemang.eskilstuna.se/",
    "X-Requested-With": "XMLHttpRequest",
    "User-Agent": "Github-Action/1.0",
}
SIZE = 250        # max items per sida

def fetch_all():
    events, page = [], 0
    while True:
        r = requests.get(API,
                         params={"page": page, "size": SIZE, "lang": "sv"},
                         headers=HEADERS,
                         timeout=30)
        if r.status_code != 200:
            raise RuntimeError(f"API status {r.status_code} på sida {page}")
        js = r.json()
        chunk = js if isinstance(js, list) else js.get("content", [])
        if not chunk:
            break
        for ev in chunk:
            title = ev.get("title") or ev.get("name") or ""
            if not title:
                continue
            url = ev.get("presentationUrl") or ev.get("url") or ""
            if url and not url.startswith("http"):
                url = "https://visiteskilstuna.se" + url
            events.append({
                "id": hashlib.sha1(url.encode()).hexdigest()[:12],
                "title": title,
                "date": (ev.get("startDate") or ev.get("date") or "")[:10],
                "url": url,
            })
        if len(chunk) < SIZE:
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
