#!/usr/bin/env python3
"""
Scrapar alla evenemangskort på Evenemangsguidens söksida och
extraherar datum, tid och plats.

- Headless Playwright (chromium)
- Klickar "Ladda fler" tills knappen är borta eller disabled
- Väntar kort efter varje klick + att antal kort ökar (om möjligt)
- Extraherar datum/tid/plats via text + regex
- Sorterar kronologiskt
- Sparar data/events_YYYY-MM-DD.json
- Fältnamn anpassade till övrig pipeline: id, title, date, time, place, link
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

        # Lazy-load: klicka “Ladda fler” tills borta eller disabled.
        # Försök också observera att antalet kort ökar efter klick.
        def normalize(n):
            try:
                return int(n)
            except Exception:
                return 0

        async def count_cards():
            els = await page.query_selector_all("article, li, div.hiq-event-card")
            return len(els)

        while True:
            before = await count_cards()
            try:
                btn = await page.wait_for_selector("button:has-text('Ladda fler')", timeout=3000)
            except PWTimeout:
                break

            # om disabled -> klart
            if await btn.get_attribute("disabled") is not None:
                break

            await btn.scroll_into_view_if_needed()
            await btn.click()

            # Vänta en liten stund på nytt innehåll
            # 1) vänta kort
            await page.wait_for_timeout(800)
            # 2) vänta att antalet kort ökar, men max ~2.5s
            try:
                await page.wait_for_function(
                    "(before) => document.querySelectorAll('article, li, div.hiq-event-card').length > before",
                    arg=before,
                    timeout=2500
                )
            except PWTimeout:
                # Om inget ökade – testa en gång till med networkidle
                await page.wait_for_load_state("networkidle", timeout=2500)

            # Om knappen försvann helt, avsluta
            try:
                await page.wait_for_selector("button:has-text('Ladda fler')", state="detached", timeout=1000)
                break
            except PWTimeout:
                pass  # finns kvar -> loopen fortsätter

        # Hämta kort
        cards = await page.query_selector_all("article, li, div.hiq-event-card")
        events = []
        today = datetime.date.today()
        seen_ids = set()

        for c in cards:
            text = (await c.inner_text()).strip()

            # Datum
            date_match = re.search(
                r"(\d{1,2})\s*(jan|feb|mar|apr|maj|jun|jul|aug|sep|okt|nov|dec)",
                text, re.IGNORECASE
            )
            if not date_match:
                continue
            day = int(date_match.group(1))
            mon_abbr = date_match.group(2).lower()
            month = MONTH_MAP.get(mon_abbr)
            if not month:
                continue
            # Om listan spänner över årsskifte: om månad < nuvarande månad => nästa år
            year = today.year + (1 if month < today.month else 0)
            date_iso = f"{year}-{month:02d}-{day:02d}"

            # Tid
            time_match = TIME_RX.search(text)
            time_str = time_match.group(1).replace(".", ":") if time_match else "00:00"

            # Plats (text efter första tidsträffen, ganska robust)
            place = ""
            if time_match:
                loc_raw = text[time_match.end():].strip()
                # Ta bort skräp i början
                place = re.sub(r"^[^A-Za-zÅÄÖåäö]+", "", loc_raw).strip()

            # Titel & URL
            a = await c.query_selector("a")
            if not a:
                continue
            raw_title = (await a.inner_text() or "").strip()
            lines = [l.strip() for l in raw_title.splitlines() if l.strip()]
            title = lines[1] if len(lines) >= 2 else (lines[0] if lines else "")
            if not title:
                continue
            href = (await a.get_attribute("href")) or ""
            if href.startswith("/"):
                href = "https://evenemang.eskilstuna.se" + href

            # Filtrera bort Utställningar om attributet finns
            cat = (await c.get_attribute("data-category")) or ""
            if "Utställningar" in cat:
                continue

            # ID på href
            ev_id = hashlib.sha1(href.encode("utf-8")).hexdigest()[:12]
            if ev_id in seen_ids:
                continue
            seen_ids.add(ev_id)

            events.append({
                "id":    ev_id,
                "title": title,
                "date":  date_iso,
                "time":  time_str,
                "place": place,   # <- standardiserat namn
                "link":  href,    # <- standardiserat namn
            })

        await browser.close()

        # Sortera kronologiskt
        events.sort(key=lambda e: (e["date"], e["time"]))

        # Spara JSON
        out_dir = pathlib.Path("data")
        out_dir.mkdir(exist_ok=True)
        path = out_dir / f"events_{today.isoformat()}.json"
        with path.open("w", encoding="utf-8") as f:
            json.dump(events, f, ensure_ascii=False, indent=2)
        print(f"Fetched {len(events)} events → {path}")

if __name__ == "__main__":
    try:
        asyncio.run(scrape())
    except Exception as e:
        print("Scraping-fel:", e, file=sys.stderr)
        sys.exit(1)
