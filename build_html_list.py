# build_html_list.py
import json
import datetime
import pathlib
import subprocess
import jinja2
import zoneinfo

# 1) Tidsstämpel i Europe/Stockholm
tz = zoneinfo.ZoneInfo("Europe/Stockholm")
now = datetime.datetime.now(tz).strftime("%Y-%m-%d %H:%M")

# 2) Datum för filnamn
today = datetime.date.today().isoformat()
yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()

data_dir = pathlib.Path("data")
cur_file = data_dir / f"events_{today}.json"

# 3) Läs dagens data
events = json.load(cur_file.open(encoding="utf-8"))

# 4) Jämför mot senaste commit om finns, annars gårdagens fil
try:
    prev_raw = subprocess.check_output(
        ["git", "show", f"HEAD:data/events_{today}.json"],
        text=True
    )
    prev_ids = {e["id"] for e in json.loads(prev_raw)}
except subprocess.CalledProcessError:
    prev_file = data_dir / f"events_{yesterday}.json"
    if prev_file.exists():
        prev_ids = {e["id"] for e in json.load(prev_file.open(encoding="utf-8"))}
    else:
        prev_ids = set()

# 5) Märk nya
for ev in events:
    ev["new"] = ev["id"] not in prev_ids

# 6) Rendera HTML
tpl = jinja2.Environment(
    loader=jinja2.FileSystemLoader("."),
    autoescape=True
).get_template("template.html")
html = tpl.render(
    STAMP_TIME=now,
    COUNT=len(events),
    events=events
)

# 7) Spara till public/index.html
pub = pathlib.Path("public")
pub.mkdir(exist_ok=True)
pub.joinpath("index.html").write_text(html, encoding="utf-8")
print("Wrote public/index.html")
