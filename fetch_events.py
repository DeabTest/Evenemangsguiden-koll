#!/usr/bin/env python3
"""
Hämtar alla evenemang från Eskilstunas REST-API och sparar dagens lista som
data/events_YYYY-MM-DD.json. Inkluderar start / sluttid, plats och kategorier.
"""
import json, datetime, pathlib, hashlib, requests, sys

API_URL   = "https://visiteskilstuna.se/rest-api/Evenemang"
PAGE_SIZE = 100
HEADERS   = {"Accept": "application/json", "User-Agent": "GitHub-Action/1.0"}

def fmt_time(iso: str) -> str:
    return iso[11:16] if iso and len(iso) >= 16 else ""

def fetch_page(page: int):
    r = requests.get(
        API_URL,
        params={"page": page, "size": PAGE_SIZE, "lang": "sv"},
        headers=HEADERS,
        timeout=30,
    )
    r.raise_for_status()
    try:
        js = r.json()
    except ValueError:
        raise RuntimeError(f"Ogil­tigt JSON-svar (sid {page})")

    if isinstance(js, list):                # list-format
        return js
    if isinstance(js, dict) and "content" in js:  # objekt-format
        return js["content"]
    raise RuntimeError(f"Oväntat JSON-format (sid {page})")

def fetch_all():
    events, page = [], 0
    while True:
        chunk = fetch_page(page)
        if not chunk:
            break
        for ev in chunk:
            if not isinstance(ev, dict):
                continue
            uid  = hashlib.sha1(str(ev.get("id")).encode()).hexdigest()[:12]
            cats = ev.get("categories") or ev.get("category") or []
            events.append({
                "id": uid,
                "title": ev.get("title", ""),
                "date":  (ev.get("startDate") or "")[:10],
                "time":  fmt_time(ev.get("startDate") or ""),
                "end":   fmt_time(ev.get("endDate") or ""),
                "location": ev.get("location", ""),
                "cats": ", ".join(cats),
                "url": "https://visiteskilstuna.se" + ev.get("presentationUrl", ""),
            })
        if len(chunk) < PAGE_SIZE:          # sista sidan
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
    out_dir = pathlib.Path("data"); out_dir.mkdir(exist_ok=True)
    path = out_dir / f"events_{stamp}.json"
    path.write_text(json.dumps(evts, ensure_ascii=False, indent=2))
    print(f"Fetched {len(evts)} events  →  {path}")

if __name__ == "__main__":
    main()
