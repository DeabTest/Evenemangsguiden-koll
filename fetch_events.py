#!/usr/bin/env python3
"""
Scrapar alla evenemangskort på Evenemangsguidens söksida.

• Klickar ”Ladda fler” tills två försök i rad inte ger fler kort
• Väntar upp till 10 s mellan klick för långsam inladdning
• Sparar data/events_YYYY-MM-DD.json
"""
import json, datetime, pathlib, hashlib, asyncio, re, time
from playwright.async_api import async_playwright, TimeoutError as PWTimeout

URL = "https://evenemang.eskilstuna.se/evenemangsguiden/evenemangsguiden/sok-evenemang"
DATE_RX = re.compile(r"\d{4}-\d{2}-\d{2}")   # YYYY-MM-DD

async def scrape():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        page = await browser.new_page()
        await page.goto(URL, wait_until="networkidle")

        prev_count, stable_rounds, clicks = 0, 0, 0
        while True:
            # hitta knappen
            try:
                btn = await page.wait_for_selector("button:has-text('Ladda fler')", timeout=5000)
            except PWTimeout:
                break
            if await btn.get_attribute("disabled") is not None:
                break

            await btn.scroll_into_view_if_needed()
            await btn.click()
            clicks += 1
            await page.wait_for_selector("button:has-text('Ladda fler')", state="detached")

            # vänta upp till 10 s på att kortantalet växer
            t0 = time.time()
            while True:
                curr_count = len(await page.query_selector_all("article, li, div.hiq-event-card"))
                if curr_count > prev_count:
                    prev_count = curr_count
                    stable_rounds = 0
                    break
                if time.time() - t0 > 10:
                    stable_rounds += 1
                    break
                await page.wait_for_timeout(500)

            if stable_rounds >= 2:
                break  # två klick i rad utan fler kort

        cards = await page.query_selector_all("article, li, div.hiq-event-card")
        events = []
        for c in cards:
            a = await c.query_selector("a")
            if not a:
                continue
            title = (await a.inner_text()).strip()
            if not title:
                continue
            url = await a.get_attribute("href") or ""
            if url and not url.startswith("http"):
                url = "https://evenemang.eskilstuna.se" + url
            raw = await c.inner_text()
            m = DATE_RX.search(raw)
            date = m.group(0) if m else ""

            events.append({
                "id":   hashlib.sha1(url.encode()).hexdigest()[:12],
                "title": title,
                "date":  date,
                "url":   url,
            })

        await browser.close()

        stamp = datetime.date.today().isoformat()
        out_dir = pathlib.Path("data"); out_dir.mkdir(exist_ok=True)
        path = out_dir / f"events_{stamp}.json"
        path.write_text(json.dumps(events, ensure_ascii=False, indent=2))
        print(f"Clicks: {clicks}  |  Fetched {len(events)} events → {path}")

if __name__ == "__main__":
    asyncio.run(scrape())
