#!/usr/bin/env python3
import json, datetime, hashlib, pathlib, sys, time, urllib.parse, requests

PROXY = "https://cozy-cobbler-0ca46b.netlify.app/.netlify/functions/rss-proxy?url="
API_BASE = "https://visiteskilstuna.se/rest-api/Evenemang/events"
PAGE_SIZE = 250

def fetch_page(page: int):
    params = {
        "count": PAGE_SIZE,
        "filters": "{}",
        "page": page,
        "query": "",
        "timestamp": int(time.time() * 1000),
    }
    orig = f"{API_BASE}?{urllib.parse.urlencode(params)}"
    proxied = PROXY + urllib.parse.quote(orig, safe="")
    r = requests.get(proxied, headers={"Accept": "application/json"}, timeout=30)

    # Spara råa texten för debugging
    outdir = pathlib.Path("data"); outdir.mkdir(exist_ok=True)
    debug_path = outdir / f"proxy_page{page}.txt"
    debug_path.write_text(r.text, encoding="utf-8")
    print(f"[DEBUG] proxy_page{page}.txt ({r.status_code}, {len(r.text)} bytes)")

    if r.status_code != 200:
        raise RuntimeError(f"API {r.status_code} på page={page}")
    try:
        data = r.json()
    except Exception as e:
        raise RuntimeError(f"Invalid JSON på page={page}: {e}")

    # Avkapsla Netlify-body om det behövs
    if isinstance(data, dict) and "body" in data:
        try:
            chunk = json.loads(data["body"])
        except Exception as e:
            raise RuntimeError(f"Ogiltig JSON i proxy-body på page={page}: {e}")
    else:
        chunk = data

    if not isinstance(chunk, list):
        raise RuntimeError(f"Fel format på API-svar page={page}: förväntade lista, fick {type(chunk)}")
    return chunk

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
    events, page = [], 0
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

    today = datetime.date.today().isoformat()
    path = pathlib.Path("data/events_" + today + ".json")
    path.write_text(json.dumps(events, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Fetched {len(events)} events → {path}")

if __name__ == "__main__":
    main()
