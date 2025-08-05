#!/usr/bin/env python3
"""
Scrapar Evenemang-fliken med Playwright.

• Klickar ”Ladda fler” tills knappen verkligen är borta
• Plockar titel, datum & url från varje kort
• Sparar data/events_YYYY-MM-DD.json
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
                # vänta max 5 s på synlig knapp
                btn = await page.wait_for_selector("button:has-text('Ladda fler')", timeout=5000)
                await btn.click()
                # vänta tills knappen *försvinner* (= laddning pågår)
                await page.wait_for_selector("button:has-text('Ladda fler')", state="detached")
                # när den dyker upp igen är nästa sida inladdad
            except PWTimeout:
                # ingen knapp längre ⇒ alla poster hämtade
                break

        cards  = await page.query_selector_all("article, li, div.hiq-event-card")
        events = []
        for c in cards:
            title = (await c.inner_text()).split("\n")[0].strip()
            if not title:
                continue
            url   = await c.eval_on_selector("a", "e=>e.href") or URL
            raw   = await c.inner_text()
            m     = DATE_RX.search(raw)
            date  = m.group(0) if m else ""

            events.append({
                "id": hashlib.sha1(url.encode()).hexdigest()[:12],
                "title": title,
                "date":  date,
                "url":   url
            })

        await browser.close()

        stamp  = datetime.date.today().isoformat()
        outdir = pathlib.Path("data"); outdir.mkdir(exist_ok=True)
        outfile = outdir / f"events_{stamp}.json"
        outfile.write_text(json.dumps(events, ensure_ascii=False, indent=2))
        print(f"Fetched {len(events)} events → {outfile}")

if __name__ == "__main__":
    asyncio.run(scrape())
