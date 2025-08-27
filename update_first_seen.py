# update_first_seen.py
import json, glob, datetime, pathlib, hashlib, sys

DATA = pathlib.Path("data")
DATA.mkdir(parents=True, exist_ok=True)

files = sorted(glob.glob("data/events_*.json"))
if not files:
    print("No events file found, skipping.")
    sys.exit(0)
latest = pathlib.Path(files[-1])

first_seen_path = DATA / "first_seen.json"
if first_seen_path.exists():
    first_seen = json.loads(first_seen_path.read_text(encoding="utf-8"))
else:
    first_seen = {}

events = json.loads(latest.read_text(encoding="utf-8"))

def eid(e):
    if e.get("id"):
        return str(e["id"])
    key = (
        (e.get("title") or "") + "|" +
        (e.get("date") or "") + "|" +
        (e.get("time") or "") + "|" +
        (e.get("place") or "") + "|" +
        (e.get("link") or e.get("url") or "")
    )
    return hashlib.sha1(key.encode("utf-8")).hexdigest()

today = datetime.date.today().isoformat()
added = 0

for e in events:
    _id = eid(e)
    if _id not in first_seen:
        first_seen[_id] = {
            "first_seen": today,
            "title": e.get("title",""),
            "link": e.get("link") or e.get("url") or "",
            "date": e.get("date",""),
            "time": e.get("time",""),
            "place": e.get("place",""),
        }
        added += 1

first_seen_path.write_text(
    json.dumps(first_seen, ensure_ascii=False, indent=2),
    encoding="utf-8"
)
print(f"first_seen updated with {added} new items")
