#!/usr/bin/env python3
"""
Scrapar alla evenemangskort på Evenemangsguidens söksida, och
extraherar korrekt datum, tid och plats.

• Headless Playwright
• Klickar “Ladda fler” tills knappen är borta eller disabled
• Väntar 1,5 s efter varje klick
• Rensar titeln från datum och tid
• Plockar datum, tid och plats med regex
• Markerar nya events via föregående fil
• Sorterar och sparar data/events_YYYY-MM-DD.json
"""
import json
import datetime
import pathlib
import hashlib
import asyncio
import re
import sys
from playwright.async_api import async_playwright, TimeoutError as PWTimeout

# --- KONFIGURATION ---
URL = (
    "https://evenemang.eskilstuna.se/"
    "evenemangsguiden/evenemangsguiden/sok-evenemang"
)
DATE_RX = re.compile(r"\d{2} [a-z]{3}(?: – \d{2} [a-z]{3})?", re.IGNORECASE)
TIME_RX = re.compile(r"\d{1,2}[.:]\d{2}")
DATA_DIR = pathlib.Path("data")
DATA_DIR.mkdir(exist_ok=True)
TODAY = datetime.date.today().isoformat()
OUTFILE = DATA_DIR / f"events_{TODAY}.json"

def gen_id(href: str) -> str:
    return hashlib.sha1(href.encode()).hexdigest()[:12]

def load_previous_ids() -> set:
    files = sorted(DATA_DIR.glob("events_*.json"))
    if len(files) < 2:
        return set()
    prev = json.loads(files[-2].read_text(encoding="utf-8"))
    return {e["id"] for e in prev}

async def scrape_events() -> list[dict]:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        page = await browser.new_page()
        await page.goto(URL, wait_until="networkidle")

        # Klicka “Ladda fler” tills gone/disabled
        while True:
            try:
                btn = await page.wait_for_selector("button:has-text('Ladda fler')", timeout=5000)
            except PWTimeout:
                break
            if await btn.get_attribute("disabled"):
                break
            await btn.click()
            await page.wait_for_timeout(1500)

        cards = await page.query_selector_all("article, li, div.hiq-event-card")
        events = []

        for c in cards:
            text = await c.inner_text()

            # Hitta href
            a = await c.query_selector("a")
            if not a:
                continue
            href = (await a.get_attribute("href") or "").strip()
            if href.startswith("/"):
                href = "https://evenemang.eskilstuna.se" + href

            # Rå titel = allt i <a>
            raw_title = (await a.inner_text()).strip()

            # Rensa bort datum- och tidsrader från titeln
            lines = [ln.strip() for ln in raw_title.splitlines() if ln.strip()]
            title_lines = [
                ln for ln in lines
                if not DATE_RX.fullmatch(ln) and not TIME_RX.search(ln)
            ]
            title = title_lines[0] if title_lines else lines[0]

            # Datum
            m_date = DATE_RX.search(text)
            date = m_date.group(0) if m_date else ""

            # Tid
            m_time = TIME_RX.search(text)
            time_str = m_time.group(0) if m_time else ""

            # Plats: första ”icke-datum/tid”-raden efter tid
            location = ""
            if m_time:
                tail = text[m_time.end():].splitlines()
                for ln in tail:
                    ln = ln.strip()
                    if not ln or TIME_RX.search(ln) or DATE_RX.fullmatch(ln):
                        continue
                    # ta bort icke-bokstav i början
                    location = re.sub(r"^[^A-Za-zÅÄÖåäö]+", "", ln)
                    break

            # Filtrera Utställningar
            cat = await c.get_attribute("data-category") or ""
            if "Utställningar" in cat:
                continue

            ev = {
                "id":       gen_id(href),
                "title":    title,
                "date":     date,
                "time":     time_str,
                "location": location,
                "url":      href,
            }
            events.append(ev)

        await browser.close()
        return events

def mark_new(events: list[dict]) -> None:
    prev_ids = load_previous_ids()
    for ev in events:
        ev["new"] = ev["id"] not in prev_ids

def main():
    try:
        events = asyncio.run(scrape_events())
        mark_new(events)
        # Sortera snyggt
        events.sort(key=lambda e: (e["date"], e["time"], e["title"]))
        with OUTFILE.open("w", encoding="utf-8") as f:
            json.dump(events, f, ensure_ascii=False, indent=2)
        print(f"Fetched {len(events)} events → {OUTFILE}")
    except Exception as e:
        print("Scraping-fel:", e, file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
