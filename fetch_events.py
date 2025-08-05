#!/usr/bin/env python3
"""
Scrapar alla evenemangskort från Evenemangsguidens söksida med DOM-baserad extraktion:

• Headless Playwright
• Klickar “Ladda fler” tills knappen är borta eller inaktiverad
• Väntar 1,5 s efter varje klick för att korten ska hinna renderas
• Extraherar datum, titel, tid och plats från dedikerade element
• Sparar JSON i data/events_YYYY-MM-DD.json
"""
import asyncio
import json
import datetime
import pathlib
import hashlib
import sys

from playwright.async_api import async_playwright, TimeoutError as PWTimeout

URL = (
    "https://evenemang.eskilstuna.se/"
    "evenemangsguiden/evenemangsguiden/sok-evenemang"
)

CARD_SELECTOR       = "li.hiq-event-card"
DATE_SELECTOR       = "time.hiq-event-card__date"
TITLE_SELECTOR      = "a.hiq-event-card__link"
TIME_SELECTOR       = "time.hiq-event-card__time"
LOCATION_SELECTOR   = "div.hiq-event-card__location"

async def scrape():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        page = await browser.new_page()
        await page.goto(URL, wait_until="networkidle")

        # Lazy-load: klicka "Ladda fler" tills knappen försvinner eller disabled
        while True:
            try:
                btn = await page.wait_for_selector("button:has-text('Ladda fler')", timeout=5000)
            except PWTimeout:
                break
            if await btn.get_attribute("disabled") is not None:
                break
            await btn.scroll_into_view_if_needed()
            await btn.click()
            # vänta tills nya kort laddats in
            await page.wait_for_selector("button:has-text('Ladda fler')", state="detached")
            await page.wait_for_timeout(1500)

        cards = await page.query_selector_all(CARD_SELECTOR)
        events = []

        for c in cards:
            # Datum
            date_el = await c.query_selector(DATE_SELECTOR)
            date = (await date_el.text_content()).strip() if date_el else ""

            # Titel & URL
            title_el = await c.query_selector(TITLE_SELECTOR)
            if not title_el:
                continue
            title = (await title_el.text_content()).strip()
            href = (await title_el.get_attribute("href")) or ""
            if href.startswith("/"):
                href = "https://evenemang.eskilstuna.se" + href

            # Tid
            time_el = await c.query_selector(TIME_SELECTOR)
            time_str = (await time_el.text_content()).strip() if time_el else ""

            # Plats
            loc_el = await c.query_selector(LOCATION_SELECTOR)
            location = (await loc_el.text_content()).strip() if loc_el else ""

            # Filtrera bort Utställningar om relevant
            cat = await c.get_attribute("data-category") or ""
            if "Utställningar" in cat:
                continue

            # Generera unikt ID från URL
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
    stamp = datetime.date.today().isoformat()
    out_dir = pathlib.Path("data")
    out_dir.mkdir(exist_ok=True)
    path = out_dir / f"events_{stamp}.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)
    print(f"Fetched {len(events)} events → {path}")

if __name__ == "__main__":
    try:
        asyncio.run(scrape())
    except Exception as e:
        print("Scraping-fel:", e, file=sys.stderr)
        sys.exit(1)
