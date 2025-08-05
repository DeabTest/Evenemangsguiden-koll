#!/usr/bin/env python3
"""
UI-scraping av Evenemangsguiden:
– Klickar “Ladda fler” tills inga fler kort
– Extraherar datum, titel & URL från varje <li> med klassen hiq-events-search__search-results--hits__hit
– Filtrerar bort Utställningar
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
DATE_SELECTOR      = "time"  # om ett <time> finns; annars justera

def fetch_events():
    events = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(START_URL, wait_until="networkidle")

        # Klicka “Ladda fler” tills knappen försvinner
        while True:
            btn = page.query_selector(LOAD_MORE_SELECTOR)
            if not btn:
                break
            btn.click()
            page.wait_for_timeout(2000)
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(2000)

        # Hämta alla kort
        cards = page.query_selector_all(CARD_SELECTOR)
        for card in cards:
            # Extrahera länk, titel & datum
            a = card.query_selector(LINK_SELECTOR)
            time_el = card.query_selector(DATE_SELECTOR)

            title = a.get_attribute("title") or a.text_content().strip() if a else ""
            url   = a.get_attribute("href") or ""
            date  = (time_el.get_attribute("datetime") or time_el.text_content().strip()) if time_el else ""

            # Hoppa över Utställningar
            # (om kortet har data-kategori, justera vid behov)
            if "Utställningar" in (card.get_attribute("data-category") or ""):
                continue

            if not (title and url and date):
                continue

            # Skapa unikt ID
            _id = hashlib.sha1(url.encode()).hexdigest()[:12]
            events.append({"id": _id, "title": title, "date": date, "url": url})

        browser.close()

    # Ta bort dubbletter
    seen, dedup = set(), []
    for ev in events:
        if ev["id"] not in seen:
            seen.add(ev["id"])
            dedup.append(ev)
    return dedup

def main():
    try:
        evs = fetch_events()
    except Exception as e:
        print("Scraping-fel:", e, file=sys.stderr)
        sys.exit(1)

    today = datetime.date.today().isoformat()
    outdir = pathlib.Path("data"); outdir.mkdir(exist_ok=True)
    path = outdir / f"events_{today}.json"
    path.write_text(json.dumps(evs, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Fetched {len(evs)} events → {path}")

if __name__ == "__main__":
    main()
