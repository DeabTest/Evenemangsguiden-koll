#!/usr/bin/env python3
"""
Scrapar Evenemang-fliken med Playwright.

• Klickar “Ladda fler” tills knappen verkligen är borta
• Hämtar titel, datum och länk för varje kort
• Sparar data/events_YYYY-MM-DD.json
"""
import json, datetime, pathlib, hashlib, asyncio, re
from playwright.async_api import async_playwright, TimeoutError as PWTimeout

URL     = "https://evenemang.eskilstuna.se/evenemangsguiden/evenemangsguiden/sok-evenemang"
DATE_RX = re.compile(r"\d{4}-\d{2}-\d{2}")   # YYYY-MM-DD

async def scrape():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        page    = await browser.new_page()
        await page.goto(URL, wait_until="networkidle")

        while True:
            try:
                btn = await page.wait_for_selector("button:has-text('Ladda fler')",
                                                   timeout=5000)
                await btn.click()
                await page.wait_for_selector("button:has-text('Ladda fler')",
                                             state="detached")
            except PWTimeout:
                break

        cards  = await page.query_selector_all("article, li, div.hiq-event-card")
        events = []
        for c in cards:
            title = (await c.inner_text()).split("\n")[0].strip()
            if not title:
                continue
            url  = await c.eval_on_selector("a", "e=>e.href") or URL
            raw  = await c.inner_text()
            m    = DATE_RX.search(raw)
            date = m.group(0) if m else ""
            events.append({
                "id":   hashlib.sha1(url.encode()).hexdigest()[:12],
                "title": title,
                "date":  date,
                "url":   url,
            })

        stamp   = datetime.date.today().isoformat()
        out_dir = pathlib.Path("data"); out_dir.mkdir(exist_ok=True)
        (out_dir / f"events_{stamp}.json").write_text(
            json.dumps(events, ensure_ascii=False, indent=2))
        print(f"Fetched {len(events)} events")

if __name__ == "__main__":
    asyncio.run(scrape())
