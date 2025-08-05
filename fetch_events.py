#!/usr/bin/env python3
"""
Scrapar alla evenemangskort på Evenemangsguidens söksida, och
extraherar korrekt datum, tid och plats med rätt mellanslag.

• Headless Playwright
• Klickar “Ladda fler” tills knappen är borta eller disabled
• Väntar 1,5 s efter varje klick
• Plockar titel via <a>
• Plockar datum via DATE_RX, tid via TIME_RX
• Plockar plats som separat rad efter tiden
• Sparar data/events_YYYY-MM-DD.json
• Skriver ut evenemangen i formatet: 06 dec Titel 18.00 Plats
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
TIME_RX = re.compile(r"\d{1,2}[.:]\d{2}")     # hh:mm eller h.mm

async def scrape():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        page = await browser.new_page()
        await page.goto(URL, wait_until="networkidle")

        # Lazy-load: klicka “Ladda fler” tills borta eller disabled
        while True:
            try:
                btn = await page.wait_for_selector("button:has-text('Ladda fler')", timeout=5000)
            except PWTimeout:
                break
            if await btn.get_attribute("disabled") is not None:
                break
            await btn.scroll_into_view_if_needed()
            await btn.click()
            await page.wait_for_selector("button:has-text('Ladda fler')", state="detached")
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

            # Plats: försök plocka separat rad efter tiden
            location = ""
            if m_time:
                lines = [line.strip() for line in text.splitlines() if line.strip()]
                for i, line in enumerate(lines):
                    if m_time.group(0) in line:
                        if i + 1 < len(lines):
                            loc_candidate = lines[i + 1]
                            if not TIME_RX.search(loc_candidate):
                                location = loc_candidate
                        break

            # Filtrera bort Utställningar
            cat = await c.get_attribute("data-category") or ""
            if "Utställningar" in cat:
                continue

            # Generera ID
            ev_id = hashlib.sha1(href.encode()).hexdigest()[:12]

            events.append({
                "id":       ev_id,
                "title":    title,
                "date":     date,
                "time":     time_str,
                "location": location,
                "url":      href,
            })

        await browser.close()

    # Spara JSON
    today = datetime.date.today().isoformat()
    out_dir = pathlib.Path("data")
    out_dir.mkdir(exist_ok=True)
    path = out_dir / f"events_{today}.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)

    # Skriv ut i formatet: 06 dec Titel 18.00 Plats
    for ev in events:
        try:
            dt = datetime.datetime.strptime(ev["date"], "%Y-%m-%d")
            date_str = dt.strftime("%d %b").lower()
        except:
            date_str = ev["date"]
        print(f"{date_str} {ev['title']} {ev['time']} {ev['location']}")

    print(f"\nFetched {len(events)} events → {path}")

if __name__ == "__main__":
    try:
        asyncio.run(scrape())
    except Exception as e:
        print("Scraping-fel:", e, file=sys.stderr)
        sys.exit(1)
