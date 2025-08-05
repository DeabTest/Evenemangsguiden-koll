#!/usr/bin/env python3
"""
Hämtar alla evenemang från Eskilstunas REST-API och sparar dagens lista som
data/events_YYYY-MM-DD.json – inkl. start/sluttid, plats och kategorier.

Om API-svaret har okänt format loggas de första 500 tecknen i Actions-loggen
så vi kan felsöka utan att skriptet kraschar på syntaxfel.
"""
import json, datetime, pathlib, hashlib, requests, sys

API_URL   = "https://visiteskilstuna.se/rest-api/Evenemang"
PAGE_SIZE = 100
HEADERS   = {"Accept": "application/json", "User-Agent": "GitHub-Action/1.0"}

def fmt_time(iso: str) -> str:
    return iso[11:16] if iso and len(iso) >= 16 else ""

def parse_response(js, page: int):
    """Returnerar listan med event eller kastar fel om okänt format."""
    if isinstance(js, list):
        return js
    if isinstance(js, dict):
        if "content" in js and isinstance(js["content"], list):
            return js["content"]
        for key in ("results", "items", "data", "hits"):
            if key in js and isinstance(js[key], list):
                return js[key]
    raise RuntimeError(f"Oväntat JSON-format (sid {page})")

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
        print("RAW-svar (första 500 tecken):", r.text[:500], file=sys.stderr)
        raise RuntimeError(f"Ogil­tigt JSON från API (sid {page})")
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
