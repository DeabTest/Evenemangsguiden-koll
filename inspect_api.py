#!/usr/bin/env python3
"""
Kör ett enda API-anrop och skriver ut allt vi får tillbaka
(så vi ser varför listan blir tom).
"""
import requests, json, pathlib

API = "https://visiteskilstuna.se/rest-api/Evenemang"
HEAD = {
    "Accept": "application/json",
    "Referer": "https://evenemang.eskilstuna.se/",
    "X-Requested-With": "XMLHttpRequest",
    "User-Agent": "Github-Action/1.0",
}

r = requests.get(API, params={"page": 0, "size": 50},
                 headers=HEAD, timeout=30)

print("HTTP-status:", r.status_code)
print("Headers   :", r.headers.get('content-type'))
text = r.text
print("Första ~4000 tecken av svaret:\n")
print(text[:4000])

# spara hela svaret för djupare titt
path = pathlib.Path("data/api_debug.json")
path.write_text(text)
print(f"\nHela svaret sparat i {path}\n")
