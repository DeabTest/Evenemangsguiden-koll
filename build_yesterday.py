# build_yesterday.py
import json, datetime, pathlib, html, sys

data_path = pathlib.Path("data/first_seen.json")
public = pathlib.Path("public")
public.mkdir(exist_ok=True)

if not data_path.exists():
    print("No first_seen.json yet; skipping publish.")
    sys.exit(0)

public.joinpath("first_seen.json").write_text(
    data_path.read_text(encoding="utf-8"),
    encoding="utf-8"
)

data = json.loads(data_path.read_text(encoding="utf-8"))
y = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
items = [v for v in data.values() if v.get("first_seen") == y]
items.sort(key=lambda x: (x.get("date",""), x.get("title","")))

rows = []
for e in items:
    title = html.escape(e.get("title",""))
    link  = e.get("link") or ""
    date  = html.escape(e.get("date",""))
    time  = html.escape(e.get("time",""))
    place = html.escape(e.get("place",""))
    title_html = f'<a href="{link}">{title}</a>' if link else title
    meta = " • ".join([v for v in [date, time, place] if v])
    rows.append(f"<li>{title_html}{(' — ' + meta) if meta else ''}</li>")

html_doc = f"""<!doctype html>
<meta charset="utf-8">
<title>Nya evenemang {y}</title>
<h1>Nya evenemang {y}</h1>
<p>Antal: {len(items)}</p>
<ul>
{''.join(rows)}
</ul>
"""
public.joinpath("yesterday.html").write_text(html_doc, encoding="utf-8")
print(f"Published yesterday.html with {len(items)} items.")
