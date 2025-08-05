#!/usr/bin/env python3
"""
Hämtar alla evenemangskort (Evenemang-fliken) med Playwright.

• Klickar “Ladda fler” tills antalet kort slutar växa två klick i rad
• Vilar 1,5 s efter varje klick så sidan hinner rendera de sista korten
• Sparar data/events_YYYY-MM-DD.json
"""
import json, datetime, pathlib, hashlib, asyncio, re
from playwright.async_api import async_playwright, TimeoutError as PWTimeout

URL = "https://evenemang.eskilstuna.se/evenemangsguiden/evenemangsguiden/sok-evenemang"
DATE_RX = re.compile(r"\d{4}-\d{2}-\d{2}")           # YYYY-MM-DD

async def scrape():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        page = await browser.new_page()
        await page.goto(URL, wait_until="networkidle")

        stable_rounds = 0          # räknar klick då korten inte växer
        prev_count = 0

        while True:
            # hitta knappen om den finns
            try:
                btn = await page.wait_for_selector(
                    "button:has-text('Ladda fler')", timeout=5000
                )
            except PWTimeout:
                break                              # ingen knapp inom 5 s

            if await btn.get_attribute("disabled") is not None:
                break                              # knappen finns men är grå

            await btn.scroll_into_view_if_needed()
            await btn.click()

            # vänta tills knappen försvinner (=begynner laddning)
            await page.wait_for_selector(
                "button:has-text('Ladda fler')", state="detached"
            )
            await page.wait_for_timeout(1500)      # buffert för rendering

            # kolla om antalet kort växte
            curr_count = len(
                await page.query_selector_all("article, li, div.hiq-event-card")
            )
            if curr_count == prev_count:
                stable_rounds += 1
                if stable_rounds >= 2:
                    break                          # två klick i rad → klart
            else:
                stable_rounds = 0
                prev_count = curr_count

        # slutlig insamling
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
        out = pathlib.Path("data"); out.mkdir(exist_ok=True)
        path = out / f"events_{stamp}.json"
        path.write_text(json.dumps(events, ensure_ascii=False, indent=2))
        print(f"Fetched {len(events)} events → {path}")

if __name__ == "__main__":
    asyncio.run(scrape())
