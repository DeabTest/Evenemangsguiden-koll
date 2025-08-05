#!/usr/bin/env python3
"""
Scrapar alla evenemangskort på Evenemangsguidens söksida, och
extraherar korrekt datum, tid och plats med rätt mellanslag.

• Headless Playwright
• Klickar “Ladda fler” tills inga nya kort dyker upp
• Väntar 2 s efter varje klick
• Plockar titel via <a>
• Plockar datum via DATE_RX, tid via TIME_RX
• Plockar plats efter tid, rensat och med mellanslag
• Sparar data/events_YYYY-MM-DD.json
• Skriver bara ut hur många event som hämtats
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

        # Klicka “Ladda fler” tills inga nya kort dyker upp
        previous_count = -1
        while True:
            cards = await page.query_selector_all("article, li, div.hiq-event-card")
            current_count = len(cards)
            if current_count == previous_count:
                break
            previous_count = current_count
            btn = await page.query_selector("button:has-text('Ladda fler')")
            if not btn:
                break
            await btn.scroll_into_view_if_needed()
            await btn.click()
            await page.wait_for_timeout(2000)  # ge tid att ladda nya kort

        # Hämta kort
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

            # Plats: efter tiden, rensad
            location = ""
            if m_time:
                after_time = text[m_time.end():].strip()
                after_time = re.sub(r"^[^\wÅÄÖåäö]+", "", after_time)
                words = after_time.split()
                location_words = []
                for word in words:
                    if TIME_RX.search(word):
                        break
                    location_words.append(word)
                    if len(location_words) >= 6:
                        break
                location = " ".join(location_words)

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

    # Endast sammanfattning i terminalen
    print(f"Fetched {len(events)} events → {path}")

if __name__ == "__main__":
    try:
        asyncio.run(scrape())
    except Exception as e:
        print("Scraping-fel:", e, file=sys.stderr)
        sys.exit(1)
