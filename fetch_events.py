#!/usr/bin/env python3
"""
Scrapar Evenemangs-fliken med Playwright (headless-Chromium).

• Går till söksidan
• Klickar “Ladda fler” tills knappen är borta eller inaktiv
• Sparar titel, datum och url för varje kort
"""

import json, datetime, pathlib, hashlib, asyncio, re
from playwright.async_api import async_playwright, TimeoutError as PWTimeout

URL      = "https://evenemang.eskilstuna.se/evenemangsguiden/evenemangsguiden/sok-evenemang"
DATE_RX  = re.compile(r"\d{4}-\d{2}-\d{2}")   # YYYY-MM-DD

async def scrape():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        page    = await browser.new_page()
        await page.goto(URL, wait_until="networkidle")

        while True:
            try:
                btn = await page.wait_for_selector("button:has-text('Ladda fler')", timeout=5000)
                # Om knappen är inaktiv (<button disabled>) → klart
                disabled = await btn.get_attribute("disabled")
                if disabled is not None:
                    break
                await btn.scroll_into_view_if_needed()
                await btn.click()
                # Vänta tills knappen försvinner (laddning pågår) …
                await page.wait_for_selector("button:has-text('Ladda fler')", state="detached")
            except PWTimeout:
                # Ingen knapp hittades inom 5 s → klart
                break

        cards  = await page.query_selector_all("article, li, div.hiq-event-card")
        events = []
        for c in cards:
            anchor = await c.query_selector("a")
            if not anchor:
                continue
            title = (await anchor.inner_text()).strip()
            if not title:
                continue
            url   = await anchor.get_attribute("href")
            if not url.startswith("http"):
                url = "https://evenemang.eskilstuna.se" + url
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
        path    = out_dir / f"events_{stamp}.json"
        path.write_text(json.dumps(events, ensure_ascii=False, indent=2))
        print(f"Fetched {len(events)} events → {path}")

if __name__ == "__main__":
    asyncio.run(scrape())
