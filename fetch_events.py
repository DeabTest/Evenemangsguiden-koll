#!/usr/bin/env python3
"""
UI-scraping av Evenemangsguiden:
– Navigerar till söksidan
– Väntar på att korten laddas
– Klickar “Ladda fler” + scrollar tills inga fler kort
– Extraherar datum, titel & URL från varje <li class="hiq-events-search__search-results--hits__hit">
– Filtrerar bort “Utställningar”
– Sparar JSON i data/events_YYYY-MM-DD.json
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
    events = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        # 1) Gå till sidan och vänta på nätverksaktivitet
        page.goto(START_URL, wait_until="networkidle")
        # 2) Vänta tills minst ett kort syns (upp till 10 s)
        page.wait_for_selector(CARD_SELECTOR, timeout=10000)

        # 3) Klicka “Ladda fler” tills knappen försvinner
        while True:
            btn = page.query_selector(LOAD_MORE_SELECTOR)
            if not btn:
                break
            btn.click()
            page.wait_for_timeout(2000)
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(2000)

        # 4) Extrahera alla kort
        cards = page.query_selector_all(CARD_SELECTOR)
        for card in cards:
            a = card.query_selector(LINK_SELECTOR)
            if not a:
                continue

            # URL och titel
            href = a.get_attribute("href") or ""
            title_attr = a.get_attribute("title")
            text = a.text_content() or ""
            title = (title_attr or text).strip()

            # Datum
            date = ""
            time_el = card.query_selector(DATE_SELECTOR)
            if time_el:
                date = (time_el.get_attribute("datetime") or time_el.text_content() or "").strip()

            # Filtrera bort Utställningar om relevant
            if "Utställningar" in (card.get_attribute("data-category") or ""):
                continue

            if not (href and title and date):
                continue

            # Absolut URL
            if href.startswith("/"):
                href = "https://evenemang.eskilstuna.se" + href

            # Generera ID
            ev_id = hashlib.sha1(href.encode()).hexdigest()[:12]
            events.append({
                "id":    ev_id,
                "title": title,
                "date":  date,
                "url":   href,
            })

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
    outdir = pathlib.Path("data")
    outdir.mkdir(exist_ok=True)
    path = outdir / f"events_{today}.json"
    path.write_text(json.dumps(evs, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Fetched {len(evs)} events → {path}")

if __name__ == "__main__":
    main()
