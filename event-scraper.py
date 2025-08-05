import json, asyncio, hashlib, datetime, os
from pathlib import Path
from playwright.async_api import async_playwright

START_URL = (
    "https://evenemang.eskilstuna.se/"
    "evenemangsguiden/evenemangsguiden/sok-evenemang"
)

OUT_DIR = Path("data")          # katalog i repo:t
OUT_DIR.mkdir(exist_ok=True)

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(START_URL, timeout=60000)

        # klicka "Ladda fler" tills knappen försvinner
        while True:
            try:
                btn = await page.wait_for_selector("text=Ladda fler", timeout=3_000)
                await btn.click()
                await page.wait_for_timeout(1200)
            except Exception:
                break

        cards = await page.query_selector_all("article.teaser, div.teaser")
        events = []
        for c in cards:
            title = (await c.query_selector("h2, h3")).inner_text()
            date  = (await c.query_selector(".date, .eventDate")).inner_text()
            link  = await (await c.query_selector("a")).get_attribute("href")
            hid   = hashlib.sha1(f"{title}{date}".encode()).hexdigest()[:12]
            events.append({"id": hid, "title": title, "date": date, "url": link})

        stamp = datetime.date.today().isoformat()
        out_file = OUT_DIR / f"events_{stamp}.json"
        out_file.write_text(json.dumps(events, ensure_ascii=False, indent=2))
        print(f"Scraped {len(events)} events -> {out_file}")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
