#!/usr/bin/env python3
"""
Hämtar alla evenemang från Eskilstunas REST-API och sparar dagens lista som
data/events_YYYY-MM-DD.json – nu inklusive sluttid, plats och kategori.
"""
import json, datetime, pathlib, hashlib, requests, sys

API_URL   = "https://visiteskilstuna.se/rest-api/Evenemang"
PAGE_SIZE = 100          # max poster per API-kall

def fmt_time(iso):
    """ISO-string → HH:MM (eller '')"""
    return iso[11:16] if iso and len(iso) >= 16 else ""

def fetch_all():
    events, page = [], 0
    while True:
        r = requests.get(
            API_URL,
            params={"page": page, "size": PAGE_SIZE, "lang": "sv"},
            timeout=30,
        )
        r.raise_for_status()
        js = r.json()

        for ev in js["content"]:
            uid  = hashlib.sha1(str(ev["id"]).encode()).hexdigest()[:12]
            cats = ev.get("categories") or ev.get("category") or []
            events.append({
                "id":   uid,
                "title": ev["title"],
                "date":  ev["startDate"][:10],              # YYYY-MM-DD
                "time":  fmt_time(ev["startDate"]),
                "end":   fmt_time(ev.get("endDate") or ""),
                "location": ev.get("location") or "",
                "cats": ", ".join(cats),
                "url":  "https://visiteskilstuna.se" + ev["presentationUrl"],
            })

        if page + 1 >= js["totalPages"]:
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
    print(f"Fetched {len(evts)} events -> {outfile}")

if __name__ == "__main__":
    main()
