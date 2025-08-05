#!/usr/bin/env python3
"""
Hämtar alla evenemang via REST-API:et och sparar dagens lista som
data/events_YYYY-MM-DD.json – inkluderar start-/sluttid, plats och kategorier.
Robust mot både objekt- och list-svar.
"""
import json, datetime, pathlib, hashlib, requests, sys

API_URL   = "https://visiteskilstuna.se/rest-api/Evenemang"
PAGE_SIZE = 100          # max poster per anrop

def fmt_time(iso):
    return iso[11:16] if iso and len(iso) >= 16 else ""

def fetch_page(page):
    """Returnerar listan med event för angiven page."""
    r = requests.get(API_URL,
                     params={"page": page, "size": PAGE_SIZE, "lang": "sv"},
                     timeout=30)
    r.raise_for_status()
    js = r.json()
    # API kan svara med listan direkt eller med {"content":[…]}
    return js["content"] if isinstance(js, dict) and "content" in js else js

def fetch_all():
    events, page = [], 0
    while True:
        chunk = fetch_page(page)
        if not chunk:                  # tomt svar → klart
            break
        for ev in chunk:
            uid  = hashlib.sha1(str(ev.get("id")).encode()).hexdigest()[:12]
            cats = ev.get("categories") or ev.get("category") or []
            events.append({
                "id":   uid,
                "title": ev.get("title", ""),
                "date":  (ev.get("startDate") or "")[:10],
                "time":  fmt_time(ev.get("startDate") or ""),
                "end":   fmt_time(ev.get("endDate") or ""),
                "location": ev.get("location", ""),
                "cats": ", ".join(cats),
                "url":  "https://visiteskilstuna.se" + ev.get("presentationUrl", ""),
            })
        if len(chunk) < PAGE_SIZE:     # sista sidan
            break
        page += 1
    return events

def main():
    try:
        evts = fetch_all()
    except Exception as exc:
        print(f"API-fel: {exc}", file=sys.stderr)
        sys.exit(1)

    stamp = datetime.date.today().isoformat()
    out = pathlib.Path("data"); out.mkdir(exist_ok=True)
    path = out / f"events_{stamp}.json"
    path.write_text(json.dumps(evts, ensure_ascii=False, indent=2))
    print(f"Fetched {len(evts)} events → {path}")

if __name__ == "__main__":
    main()
