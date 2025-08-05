#!/usr/bin/env python3
"""
UI-scraping av Evenemangsguiden:
– Klickar “Ladda fler” tills inga fler finns
– Extraherar datum, titel & URL från varje <li class="hiq-events-search__...__hit">
– Filtrerar bort “Utställningar”
– Sparar data/events_ÅÅÅÅ-MM-DD.json
"""
import hashlib
import json
import datetime
import pathlib
import sys
from playwright.sync_api import sync_playwright

START_URL          = "https://evenemang.eskilstuna.se/evenemangsguiden/evenemangsguiden/sok-evenemang"
LOAD_MORE_SELECTOR = "button:has-text('Ladda fler')"
CARD_SELECTOR      = "li.hiq-events-search__search-results--hits__hit"
LINK_SELECTOR      = "a.hiq-events-search__search-results--hits__hit-link"
DATE_SELECTOR      = "time"

def fetch_events():
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(START_URL, wait_until="networkidle")

        # Klicka "Ladda fler" tills knappen försvinner
        while True:
            btn = page.query_selector(LOAD_MORE_SELECTOR)
            if not btn:
                break
            btn.click()
            page.wait_for_timeout(2000)
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(2000)

        cards = page.query_selector_all(CARD_SELECTOR)
        for card in cards:
            # Titel & URL
            a = card.query_selector(LINK_SELECTOR)
            if not a:
                continue
            url = a.get_attribute("href") or ""
            # Titeln kan finnas i title-attr eller i texten
            title = a.get_attribute("title") or a.text_content().strip() or ""
            # Datum
            date = ""
            time_el = card.query_selector(DATE_SELECTOR)
            if time_el:
                dt_attr = time_el.get_attribute("datetime")
                date = dt_attr or time_el.text_content().strip()

            # Filtrera bort Utställningar (om card bär data-category)
            category = card.get_attribute("data-category") or ""
            if "Utställningar" in category:
                continue

            # Hoppa över om vi saknar nödvändiga fält
            if not (url and title and date):
                continue

            # Gör URL absolut om den är relativ
            if url.startswith("/"):
                url = "https://evenemang.eskilstuna.se" + url

            # Generera ID
            ev_id = hashlib.sha1(url.encode()).hexdigest()[:12]
            results.append({
                "id":    ev_id,
                "title": title,
                "date":  date,
                "url":   url,
            })

        browser.close()

    # Dedupe
    seen, dedup = set(), []
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
    outdir = pathlib.Path("data"); outdir.mkdir(exist_ok=True)
    path = outdir / f"events_{today}.json"
    path.write_text(json.dumps(events, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Fetched {len(events)} events → {path}")

if __name__ == "__main__":
    main()
