#!/usr/bin/env python3
"""
Hämtar alla evenemang från Eskilstunas REST-API och sparar dagens lista som
data/events_YYYY-MM-DD.json. Letar automatiskt upp den lista som innehåller
events (d.v.s. dict-objekt med 'title'-fält) – robust mot ändrat format.
"""
import json, datetime, pathlib, hashlib, requests, sys, itertools

API_URL   = "https://visiteskilstuna.se/rest-api/Evenemang"
PAGE_SIZE = 100
HEADERS   = {"Accept": "application/json", "User-Agent": "GitHub-Action/1.0"}

def find_event_list(js, _depth=0):
    """Går rekursivt igenom JSON och returnerar första listan av event-dictar."""
    if isinstance(js, list):
        if js and isinstance(js[0], dict) and "title" in js[0]:
            return js
        for item in js:
            found = find_event_list(item, _depth+1)
            if found:
                return found
    elif isinstance(js, dict):
        for v in js.values():
            found = find_event_list(v, _depth+1)
            if found:
                return found
    return None

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
    js = r.json()
    events = find_event_list(js)
    if events is None:
        raise RuntimeError(f"Kunde inte hitta event-lista i JSON (sid {page})")
    return events

def fetch_all():
    events, page = [], 0
    while True:
        chunk = fetch_page(page)
        if not chunk:
            break
        for ev in chunk:
            uid  = hashlib.sha1(str(ev.get("id") or ev.get("guid") or "").encode()).hexdigest()[:12]
            cats = ev.get("categories") or ev.get("category") or ev.get("tags") or []
            events.append({
                "id":   uid,
                "title": ev.get("title") or ev.get("name") or "",
                "date":  (ev.get("startDate") or ev.get("date") or "")[:10],
                "time":  fmt_time(ev.get("startDate") or ev.get("date") or ""),
                "end":   fmt_time(ev.get("endDate") or ""),
                "location": ev.get("location") or ev.get("place") or "",
                "cats": ", ".join(cats) if isinstance(cats, list) else str(cats),
                "url":  "https://visiteskilstuna.se" + (ev.get("presentationUrl") or ev.get("url") or ""),
            })
        if len(chunk) < PAGE_SIZE:
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
    outfile = out_dir / f"events_{stamp}.json"
    outfile.write_text(json.dumps(evts, ensure_ascii=False, indent=2))
    print(f"Fetched {len(evts)} events  →  {outfile}")

if __name__ == "__main__":
    main()
