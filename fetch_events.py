#!/usr/bin/env python3
"""
Scrapar alla evenemang via webbläsar-fetch i Playwright – korrekt
URL-enkodning av alla query-parametrar.

• Navigerar till söksidan (samma origin = inga CORS-problem)
• Kör JS som anropar fetch() med URLSearchParams tills tom lista
• Filtrerar bort “Utställningar”
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

# JavaScript som körs inifrån sidan, med rätt URLSearchParams
API_JS = """
async () => {
  const all = [];
  let page = 0;
  const size = 250;
  while (true) {
    const url = new URL('/rest-api/Evenemang/events', window.location.origin);
    url.searchParams.set('count', size);
    url.searchParams.set('filters', JSON.stringify({}));  // korrekt encoding
    url.searchParams.set('page', page);
    url.searchParams.set('query', '');
    url.searchParams.set('timestamp', Date.now());
    const res = await fetch(url.href, { credentials: 'same-origin' });
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
        # Navigera till söksidan för att få rätt cookies/session
        await page.goto(START_URL, wait_until="networkidle")
        # Kör fetch-anropet inifrån sidan
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
