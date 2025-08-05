#!/usr/bin/env python3
"""
Scrapar alla evenemangskort på Evenemangsguidens söksida, och inkluderar tid och plats.

• Öppnar sidan i headless-Chromium (Playwright)
• Klickar “Ladda fler” tills knappen är borta eller inaktiv
• Väntar 1,5 s efter varje klick så sista korten hinner renderas
• Plockar titel, datum, tid, plats och länk ur varje kort
• Sparar data/events_YYYY-MM-DD.json
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
TIME_RX = re.compile(r"\d{1,2}[:.]\d{2}")    # hh:mm or h.mm
LOC_RX  = re.compile(r"–\s*(.+)$")          # text efter ett “– ”

async def scrape():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        page = await browser.new_page()
        await page.goto(URL, wait_until="networkidle")

        # Lazy‐load: klicka “Ladda fler” tills den försvinner eller inaktiveras
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

        # Hämta alla event-kort
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
            m_loc = LOC_RX.search(text)
            location = m_loc.group(1).strip() if m_loc else ""

            # Filtrera bort Utställningar
            cat = await c.get_attribute("data-category") or ""
            if "Utställningar" in cat:
                continue

            # Generera unikt ID
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

    # Spara JSON-filen
    today = datetime.date.today().isoformat()
    out_dir = pathlib.Path("data")
    out_dir.mkdir(exist_ok=True)
    path = out_dir / f"events_{today}.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)
    print(f"Fetched {len(events)} events → {path}")

if __name__ == "__main__":
    try:
        asyncio.run(scrape())
    except Exception as e:
        print("Scraping-fel:", e, file=sys.stderr)
        sys.exit(1)
