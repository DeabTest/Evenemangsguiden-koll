#!/usr/bin/env python3
"""
Scrapar alla evenemang genom att köra fetch() inifrån sidan i Playwright.

• Navigerar till söksidan (samma origin = inga CORS-problem)
• Kör JS som loopar page=0,1,2… med count=250 tills tom lista
• Filtrerar bort Utställningar
• Sparar data/events_YYYY-MM-DD.json
"""
import asyncio
import datetime
import hashlib
import json
import pathlib
import sys

from playwright.async_api import async_playwright

START_URL = "https://evenemang.eskilstuna.se/evenemangsguiden/evenemangsguiden/sok-evenemang"

API_JS = """
async () => {
  const all = [];
  let page = 0;
  const size = 250;
  while (true) {
    // Bygg relativ URL mot samma origin
    const url = `/rest-api/Evenemang/events?count=${size}` +
                `&filters={}` +
                `&page=${page}` +
                `&query=` +
                `&timestamp=${Date.now()}`;
    const res = await fetch(url, { credentials: 'same-origin' });
    if (!res.ok) {
      throw new Error(`API ${res.status} på page=${page}`);
    }
    const chunk = await res.json();
    if (!Array.isArray(chunk) || chunk.length === 0) break;
    all.push(...chunk);
    page++;
  }
  return all;
}
"""

def normalize(item: dict):
    if item.get("categoryName") == "Utställningar":
        return None
    title = item.get("title") or item.get("name") or ""
    if not title:
        return None
    url = item.get("presentationUrl") or item.get("url") or ""
    if url and not url.startswith("http"):
        url = "https://visiteskilstuna.se" + url
    date = (item.get("startDate") or item.get("date") or "")[:10]
    return {
        "id": hashlib.sha1(url.encode()).hexdigest()[:12],
        "title": title,
        "date": date,
        "url": url,
    }

async def fetch_events():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        page = await browser.new_page()
        # Navigera till sidan för att få rätt cookies/origin
        await page.goto(START_URL, wait_until="networkidle")
        raw = await page.evaluate(API_JS)
        await browser.close()
    return [normalize(ev) for ev in raw if normalize(ev)]

def main():
    try:
        events = asyncio.run(fetch_events())
    except Exception as e:
        print("API-fel:", e, file=sys.stderr)
        sys.exit(1)

    today = datetime.date.today().isoformat()
    outdir = pathlib.Path("data"); outdir.mkdir(exist_ok=True)
    path = outdir / f"events_{today}.json"
    path.write_text(
        json.dumps(events, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"Fetched {len(events)} events → {path}")

if __name__ == "__main__":
    main()
