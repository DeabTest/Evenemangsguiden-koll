#!/usr/bin/env python3
"""
Scrapar alla evenemangskort på Evenemangsguidens söksida.

• Öppnar sidan i headless-Chromium (Playwright)
• Klickar “Ladda fler” tills knappen är borta ELLER inaktiv
• Vilar 1,5 s efter varje klick så sista korten hinner renderas
• Plockar titel, datum och länk ur varje kort
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
DATE_RX = re.compile(r"\d{4}-\d{2}-\d{2}")  # YYYY-MM-DD


async def scrape():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        page = await browser.new_page()
        await page.goto(URL, wait_until="networkidle")

        cards = []
        while True:
            # Leta efter klickbar knapp max 5 s
            try:
                btn = await page.wait_for_selector(
                    "button:has-text('Ladda fler')", timeout=5000
                )
            except PWTimeout:
                break  # ingen knapp längre

            # Avbryt om knappen är avaktiverad (<button disabled>)
            if await btn.get_attribute("disabled") is not None:
                break

            await btn.scroll_into_view_if_needed()
            await btn.click()

            # Vänta tills knappen försvinner (laddning startar)
            await page.wait_for_selector(
                "button:has-text('Ladda fler')", state="detached"
            )
            # Extra buffert så korten hinner renderas
            await page.wait_for_timeout(1500)

        # Samla alla kort efter sista laddningen
        cards = await page.query_selector_all("article, li, div.hiq-event-card")

        events = []
        for c in cards:
            anchor = await c.query_selector("a")
            if not anchor:
                continue
            title = (await anchor.inner_text()).strip()
            if not title:
                continue
            url = await anchor.get_attribute("href") or ""
            if url and not url.startswith("http"):
                url = "https://evenemang.eskilstuna.se" + url
            raw = await c.inner_text()
            m = DATE_RX.search(raw)
            date = m.group(0) if m else ""

            events.append(
                {
                    "id": hashlib.sha1(url.encode()).hexdigest()[:12],
                    "title": title,
                    "date": date,
                    "url": url,
                }
            )

        await browser.close()

        stamp = datetime.date.today().isoformat()
        out_dir = pathlib.Path("data")
        out_dir.mkdir(exist_ok=True)
        path = out_dir / f"events_{stamp}.json"
        path.write_text(json.dumps(events, ensure_ascii=False, indent=2))
        print(f"Fetched {len(events)} events → {path}")


if __name__ == "__main__":
    asyncio.run(scrape())
