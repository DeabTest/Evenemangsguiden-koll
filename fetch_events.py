#!/usr/bin/env python3
"""
Scrapar alla evenemangskort på Evenemangsguidens söksida, och
extraherar korrekt datum, tid och plats med rätt mellanslag.

• Headless Playwright
• Klickar “Ladda fler” tills knappen är borta eller disabled
• Väntar 1,5 s efter varje klick
• Plockar titel via <a>
• Plockar datum via DATE_RX, tid via TIME_RX
• Plockar plats som text efter tiden – FIXAT så den inte klistrar ihop
• Sparar data/events_YYYY-MM-DD.json
• Märker nya evenemang med "new": true
"""
import json
import datetime
import pathlib
import hashlib
import asyncio
import re
import sys
from playwright.async_api import async_playwright, TimeoutError as PWTimeout

URL = (
    "https://evenemang.eskilstuna.se/"
    "evenemangsguiden/evenemangsguiden/sok-evenemang"
)
DATE_RX = re.compile(r"\d{4}-\d{2}-\d{2}")   # YYYY-MM-DD
TIME_RX = re.compile(r"\d{1,2}[.:]\d{2}")    # hh:mm eller h.mm

DATA_DIR = pathlib.Path("data")
DATA_DIR.mkdir(exist_ok=True)
TODAY = datetime.date.today().isoformat()
OUTFILE = DATA_DIR / f"events_{TODAY}.json"

def generate_id(href):
    return hashlib.sha1(href.encode()).hexdigest()[:12]

def compare_with_previous(new_events):
    """Läs in senaste filen (om någon) och markera nya med 'new': True"""
    old_files = sorted(DATA_DIR.glob("events_*.json"))
    if not old_files:
        return new_events
    try:
        with old_files[-1].open(encoding="utf-8") as f:
            old = json.load(f)
    except Exception:
        return new_events

    old_ids = {e["id"] for e in old}
    for ev in new_events:
        if ev["id"] not in old_ids:
            ev["new"] = True
    return new_events

async def scrape():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        page = await browser.new_page()
        await page.goto(URL, wait_until="networkidle")

        # Klicka “Ladda fler” tills knappen försvinner eller är disabled
        while True:
            try:
                btn = await page.wait_for_selector("button:has-text('Ladda fler')", timeout=5000)
            except PWTimeout:
                break
            if await btn.get_attribute("disabled") is not None:
                break
            await btn.scroll_into_view_if_needed()
            await btn.click()
            await page.wait_for_timeout(1500)

        cards = await page.query_selector_all("article, li, div.hiq-event-card")
        events = []

        for c in cards:
            text = await c.inner_text()

            # Titel & URL
            a = await c.query_selector("a")
            if not a:
                continue
            title = (await a.inner_text()).strip()
            if not title:
                continue
            href = (await a.get_attribute("href")) or ""
            if href.startswith("/"):
                href = "https://evenemang.eskilstuna.se" + href

            # Datum
            m_date = DATE_RX.search(text)
            date = m_date.group(0) if m_date else ""

            # Tid
            m_time = TIME_RX.search(text)
            time_str = m_time.group(0) if m_time else ""

            # Plats
            location = ""
            if m_time:
                # Leta upp första platsrad efter tiden
                next_lines = text[m_time.end():].splitlines()
                for line in next_lines:
                    line = line.strip()
                    if line and not TIME_RX.search(line):
                        location = re.sub(r"^[^A-Za-zÅÄÖåäö]+", "", line)
                        break

            # Filtrera bort utställningar
            cat = await c.get_attribute("data-category") or ""
            if "Utställningar" in cat:
                continue

            ev_id = generate_id(href)

            events.append({
                "id":       ev_id,
                "title":    title,
                "date":     date,
                "time":     time_str,
                "location": location,
                "url":      href,
            })

        await browser.close()

    # Markera nya evenemang
    events = compare_with_previous(events)

    # Sortera
    events.sort(key=lambda e: (e["date"], e["time"], e["title"]))

    # Spara
    with OUTFILE.open("w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)

    print(f"Fetched {len(events)} events → {OUTFILE}")

if __name__ == "__main__":
    try:
        asyncio.run(scrape())
    except Exception as e:
        print("Scraping-fel:", e, file=sys.stderr)
        sys.exit(1)
