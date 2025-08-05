#!/usr/bin/env python3
"""
Scrapar Evenemangsguidens söksida med Playwright (headless-Chromium).

• Öppnar sidan
• Klickar ”Ladda fler” tills knappen försvinner
• Plockar titel, datum och länk från varje kort
• Sparar data/events_YYYY-MM-DD.json
"""

import json, datetime, pathlib, hashlib, asyncio, re
from playwright.async_api import async_playwright

URL = "https://evenemang.eskilstuna.se/evenemangsguiden/evenemangsguiden/sok-evenemang"

# regex för YYYY-MM-DD i kortens text
DATE_RX = re.compile(r"\d{4}-\d{2}-\d{2}")

async def scrape():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        page = await browser.new_page()
        await page.goto(URL, wait_until="networkidle")

        # Klicka ”Ladda fler” tills knappen försvinner/inte är klickbar
        while True:
            btn = await page.query_selector("button:has-text('Ladda fler')")
            if not btn:
                break
            try:
                await btn.click()
                await page.wait_for_timeout(700)  # låt innehåll laddas
            except Exception:
                break

        cards = await page.query_selector_all("article, li, div.hiq-event-card")
        events = []
        for c in cards:
            title = (await c.inner_text()).split("\n")[0].strip()
            if not title:
                continue
            url = await c.eval_on_selector("a", "e=>e.href") or URL
            raw = await c.inner_text()
            m   = DATE_RX.search(raw)
            date = m.group(0) if m else ""

            events.append({
                "id":   hashlib.sha1(url.encode()).hexdigest()[:12],
                "title": title,
                "date":  date,
                "url":   url
            })

        await browser.close()

        stamp = datetime.date.today().isoformat()
        outdir = pathlib.Path("data"); outdir.mkdir(exist_ok=True)
        outfile = outdir / f"events_{stamp}.json"
        outfile.write_text(json.dumps(events, ensure_ascii=False, indent=2))
        print(f"Fetched {len(events)} events  →  {outfile}")

if __name__ == "__main__":
    asyncio.run(scrape())
