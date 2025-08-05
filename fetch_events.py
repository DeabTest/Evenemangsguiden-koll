#!/usr/bin/env python3
"""
Scrapar alla evenemangskort på Evenemangsguidens söksida, och
extraherar korrekt datum, tid och plats med rätt mellanslag.

• Headless Playwright
• Klickar “Ladda fler” tills knappen är borta eller disabled
• Väntar 1,5 s efter varje klick
• Extraherar datum, tid och plats via CSS och regex
• Sorterar evenemangen kronologiskt
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

# Regex för tid, hh.mm eller h:mm
TIME_RX = re.compile(r"(\d{1,2}[.:]\d{2})")

# Svenska månadsförkortningar → månadnummer
MONTH_MAP = {
    "jan": 1,  "feb": 2,  "mar": 3,  "apr": 4,
    "maj": 5,  "jun": 6,  "jul": 7,  "aug": 8,
    "sep": 9,  "okt":10,  "nov":11,  "dec":12,
}

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
        today = datetime.date.today()

        for c in cards:
            # Hitta datum-text i kortet
            txt = await c.inner_text()

            # DATE_RX: hitta första dd mon eller dd mon - dd mon
            # Vi plockar alltid startdatum
            date_match = re.search(r"(\d{1,2})\s*(jan|feb|mar|apr|maj|jun|jul|aug|sep|okt|nov|dec)", txt, re.IGNORECASE)
            if date_match:
                day = int(date_match.group(1))
                mon_abbr = date_match.group(2).lower()
                month = MONTH_MAP[mon_abbr]
                year = today.year + (1 if month < today.month else 0)
                date_iso = f"{year}-{month:02d}-{day:02d}"
            else:
                # Hoppa över om inget datum
                continue

            # Tid
            time_match = TIME_RX.search(txt)
            time_str = ""
            if time_match:
                # normalisera punkt till kolon
                time_str = time_match.group(1).replace(".", ":")
            
            # Plats: text efter tid
            location = ""
            if time_match:
                loc_raw = txt[time_match.end():].strip()
                # ta bort inledande skiljetecken
                location = re.sub(r"^[^A-Za-zÅÄÖåäö]+", "", loc_raw)

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

            # Filtrera bort Utställningar
            cat = await c.get_attribute("data-category") or ""
            if "Utställningar" in cat:
                continue

            # Generera ID
            ev_id = hashlib.sha1(href.encode()).hexdigest()[:12]

            events.append({
                "id":       ev_id,
                "title":    title,
                "date":     date_iso,
                "time":     time_str or "00:00",
                "location": location,
                "url":      href,
            })

        await browser.close()

    # Sortera kronologiskt
    events.sort(key=lambda e: (e["date"], e["time"]))

    # Spara JSON
    out_dir = pathlib.Path("data")
    out_dir.mkdir(exist_ok=True)
    today_str = today.isoformat()
    path = out_dir / f"events_{today_str}.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)
    print(f"Fetched {len(events)} events → {path}")

if __name__ == "__main__":
    try:
        asyncio.run(scrape())
    except Exception as e:
        print("Scraping-fel:", e, file=sys.stderr)
        sys.exit(1)
