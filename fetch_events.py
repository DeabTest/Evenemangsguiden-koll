#!/usr/bin/env python3
"""
Hämtar alla evenemang genom UI-scraping med Playwright:

1) Navigerar till Evenemangsguiden
2) Klickar 'Ladda fler' + scrollar tills inga fler knapp finns
3) Extraherar date, title, url från varje kort
4) Filtrerar bort Utställningar
5) Sparar JSON i data/events_YYYY-MM-DD.json
"""
import hashlib
import json
import datetime
import pathlib
import sys

from playwright.sync_api import sync_playwright

START_URL = "https://evenemang.eskilstuna.se/evenemangsguiden/evenemangsguiden/sok-evenemang"
LOAD_MORE_SELECTOR = "button:has-text('Ladda fler')"
CARD_SELECTOR = "article, li, .hiq-event-card"

def fetch_events():
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(START_URL, wait_until="networkidle")

        # Klicka 'Ladda fler' tills knappen försvinner
        while True:
            btn = page.query_selector(LOAD_MORE_SELECTOR)
            if not btn:
                break
            btn.click()
            # vänta för rendering + scroll
            page.wait_for_timeout(2000)
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(2000)

        # Extrahera event-korten
        cards = page.query_selector_all(CARD_SELECTOR)
        for el in cards:
            # Hitta länk och datum
            a = el.query_selector("a")
            time_el = el.query_selector("time")
            title = a.text_content().strip() if a else ""
            url   = a.get_attribute("href") if a else ""
            date  = time_el.get_attribute("datetime") or time_el.text_content().strip() if time_el else ""

            # Hoppa över Utställningar eller tomma
            # (antag kategoriName som data-attribute; ej 100% säkert men pröva)
            category = el.get_attribute("data-category") or ""
            if "Utställningar" in category:
                continue
            if not (title and date and url):
                continue

            # Generera ID från URL
            _id = hashlib.sha1(url.encode()).hexdigest()[:12]
            results.append({"id": _id, "title": title, "date": date, "url": url})

        browser.close()
    # Dedupe baserat på ID (behöver inte men kan vara säkert)
    seen = set()
    dedup = []
    for ev in results:
        if ev["id"] not in seen:
            seen.add(ev["id"])
            dedup.append(ev)
    return dedup

def main():
    try:
        events = fetch_events()
    except Exception as e:
        print("Scraping-fel:", e, file=sys.stderr)
        sys.exit(1)

    today = datetime.date.today().isoformat()
    outdir = pathlib.Path("data")
    outdir.mkdir(exist_ok=True)
    path = outdir / f"events_{today}.json"
    path.write_text(json.dumps(events, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Fetched {len(events)} events → {path}")

if __name__ == "__main__":
    main()
