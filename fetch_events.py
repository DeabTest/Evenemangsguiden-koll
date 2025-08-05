#!/usr/bin/env python3
"""
Robust hämtare av evenemang från Eskilstunas REST-API.

• Loggar API-svaret på första sidan i raw-format om det inte känns igen
  (sparas som  data/debug_page0.json  i repo:t).
• Hoppar över poster som inte är dicts.
• Inkluderar start / sluttid, plats och kategorier.
"""
import json, datetime, pathlib, hashlib, requests, sys, pprint

API_URL   = "https://visiteskilstuna.se/rest-api/Evenemang"
PAGE_SIZE = 100
HEADERS   = {"Accept": "application/json", "User-Agent": "GitHub-Action/1.0"}

def fmt_time(iso: str) -> str:
    return iso[11:16] if iso and len(iso) >= 16 else ""

def parse_response(js, page: int):
    """Returnerar listan med event eller None om formatet är okänt."""
    if isinstance(js, list):
        return js
    if isinstance(js, dict):
        if "content" in js:
            return js["content"]
        # ibland ligger listan direkt under 'results' eller annat nyckelnamn
        for key in ("results", "items", "data"):
            if key in js and isinstance(js[key], list):
                return js[key]
    # okänt format
    debug = pathlib.Path("data/debug_page0.json")
    debug.write_text(json.dumps(js, ensure_ascii=False, indent=2))
    raise RuntimeError(
        f"Oväntat JSON-format (sid {page}). "
        f"Raw-svar sparat i {debug}"
    )

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
        print("RAW-svar:", r.text[:500], file=sys.stderr)   # <-- NYTT
        raise RuntimeError(f"Ogil­tigt JSON (sid {page})")
    return parse_response(js, page)

def fetch_all():
    events, page = [], 0
    while True:
        chunk = fetch_page(page)
        if not chunk:
            break
        for ev in chunk:
            if not isinstance(ev, dict):
                continue
            uid  = hashlib.sha1(str(ev.get("id") or ev.get("guid") or "").encode()).hexdigest()[:12]
            cats = ev.get("categories") or ev.get("category") or ev.get("tags") or []
            events.append({
                "id": uid,
                "title": ev.get("title") or ev.get("name") or "",
                "date":  (ev.get("startDate") or ev.get("date") or "")[:10],
                "time":  fmt_time(ev.get("startDate") or ev.get("date") or ""),
                "end":   fmt_time(ev.get("endDate") or ""),
                "location": ev.get("location") or ev.get("place") or "",
                "cats": ", ".join(cats) if isinstance(cats, list) else str(cats),
                "url": "https://visiteskilstuna.se" + (ev.get("presentationUrl") or ev.get("url") or ""),
            })
        if len(chunk) < PAGE_SIZE:
            break
        page += 1
    return events

def main():
    out_dir = pathlib.Path("data"); out_dir.mkdir(exist_ok=True)

    try:
        evts = fetch_all()
    except Exception as exc:
        print(f"API-fel: {exc}", file=sys.stderr)
        sys.exit(1)

    stamp = datetime.date.today().isoformat()
    path = out_dir / f"events_{stamp}.json"
    path.write_text(json.dumps(evts, ensure_ascii=False, indent=2))
    print(f"Fetched {len(evts)} events  →  {path}")

if __name__ == "__main__":
    main()

