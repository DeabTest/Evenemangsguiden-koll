#!/usr/bin/env python3
"""
Skriver ut REST-API-svaret (sida 0) ofiltrerat så vi kan se strukturen.
Körs bara en gång för felsökning.
"""
import json, pathlib, requests, sys

API_URL = "https://visiteskilstuna.se/rest-api/Evenemang"
HEADERS = {"Accept": "application/json", "User-Agent": "GitHub-Action/inspect"}

def main():
    r = requests.get(API_URL,
                     params={"page": 0, "size": 100, "lang": "sv"},
                     headers=HEADERS,
                     timeout=30)
    print("HTTP-status:", r.status_code)
    try:
        js = r.json()
    except ValueError:
        print("Svar är inte JSON, visar första 600 tecken:\n", r.text[:600])
        sys.exit(0)

    print("Top-nivå-nycklar i JSON:", list(js.keys())[:10])
    pretty = json.dumps(js, ensure_ascii=False, indent=2)[:4000]  # logga max 4000 tecken
    print("Första ~4000 tecken av JSON-svaret:\n", pretty)

    out = pathlib.Path("data/inspect_page0_full.json")
    out.write_text(json.dumps(js, ensure_ascii=False, indent=2))
    print(f"Hela svaret sparat i {out}")

if __name__ == "__main__":
    main()
