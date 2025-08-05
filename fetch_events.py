#!/usr/bin/env python3
"""
Scrapar alla evenemangskort på Evenemangsguidens söksida, inklusive tid och plats.

• Öppnar sidan i headless-Chromium (Playwright)
• Klickar “Ladda fler” tills knappen är borta eller inaktiv
• Vilar 1,5 s efter varje klick så sista korten hinner renderas
• Plockar titel, datum, tid, plats och länk ur varje kort
• Sparar data/events_YYYY-MM-DD.json
"""
import json
import datetime
import pathlib
import hashlib
import asyncio
import re
from playwright.async_api import async_playwright, TimeoutError as PWTimeout

URL = (
    "https://evenemang.eskilstuna.se/"
    "evenemangsguiden/evenemangsguiden/sok-evenemang"
)
DATE_RX = re.compile(r"\d{4}-\d{2}-\d{2}")   # YYYY-MM-DD
TIME_RX = re.compile(r"\d{1,2}[:.]\d{2}")    # hh:mm or h.mm
LOC_RX  = re.compile(r" – (.+)$")           # Platsen kommer ofta efter ett “– ”

async def scrape():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        page = await browser.new_page()
        await page.goto(URL, wait_until="networkidle")

        # Ladda lazy-load
        while True:
            try:
                btn = await page.wait_for_selector(
                    "button:has-text('Ladda fler')", timeout=5000
                )
            except PWTimeout:
                break
            if await btn.get_attribute("disabled") is not None:
                break
            await btn.scroll_into_view_if_needed()
            await btn.click()
            await page.wait_for_selector(
                "button:has-text('Ladda fler')", state="detached"
            )
            await page.wait_for_timeout(1500)

        # Hämta alla kort
        cards = await page.query_selector_all("article, li, div.hiq-event-card")
        events = []

        for c in cards:
            anchor = await c.query_selector("a")
            if not anchor:
                continue

            # Titel
            title = (await anchor.inner_text()).strip()
            if not title:
                continue

            # URL
            url = await anchor.get_attribute("href") or ""
            if url.startswith("/"):
                url = "https://evenemang.eskilstuna.se" + url

            # Rådata för regex-sökning
            raw = await c.inner_text()

            # Datum
            m_date = DATE_RX.search(raw)
            date = m_date.group(0) if m_date else ""

           
::contentReference[oaicite:0]{index=0}
