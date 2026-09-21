"""
Ricarica gli eventi culturali di Trieste (mostre, concerti, visite
guidate, festival, conferenze, ecc. - non solo le mostre d'arte) dal
calendario ufficiale del Comune di Trieste, triestecultura.it.

Il sito usa il plugin WordPress "The Events Calendar", che espone una
REST API pubblica standard e documentata (molto piu' stabile di uno
scraping HTML fatto a mano). Questo script legge da li' e AGGIUNGE i
risultati a data.json sotto la chiave "trieste_eventi", senza toccare
le chiavi scritte da scrape.py (mostre per provincia).
"""

import json
import sys
from datetime import date, datetime
from pathlib import Path

import requests

API_BASE = "https://triestecultura.it/wp-json/tribe/events/v1/events"
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "data.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}

MONTHS_IT = [
    "", "gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
    "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre",
]

MAX_PAGES = 3  # limite di sicurezza: max 3 * 50 = 150 eventi


def format_date(iso_str):
    """'2026-04-02 00:00:00' -> '2 aprile 2026'. None se non interpretabile."""
    if not iso_str:
        return None
    try:
        dt = datetime.strptime(iso_str[:10], "%Y-%m-%d")
    except ValueError:
        return None
    return "{} {} {}".format(dt.day, MONTHS_IT[dt.month], dt.year)


def fetch_events():
    today = date.today().isoformat()
    events = []
    page = 1
    total_pages = 1

    while page <= total_pages and page <= MAX_PAGES:
        resp = requests.get(
            API_BASE,
            params={"start_date": today, "per_page": 50, "page": page},
            headers=HEADERS,
            timeout=20,
        )
        print(
            "[debug] eventi Trieste pagina {}: status={} lunghezza_risposta={}".format(
                page, resp.status_code, len(resp.text)
            ),
            file=sys.stderr,
        )
        resp.raise_for_status()
        data = resp.json()

        total_pages = data.get("total_pages", 1) or 1
        raw_events = data.get("events", [])
        print(
            "[debug] eventi Trieste pagina {}: {} eventi nella risposta, total_pages={}".format(
                page, len(raw_events), total_pages
            ),
            file=sys.stderr,
        )

        for ev in raw_events:
            title = (ev.get("title") or "").strip()
            if not title:
                continue

            venue_info = ev.get("venue") or {}
            venue = (venue_info.get("venue") or "").strip()

            start_fmt = format_date(ev.get("start_date"))
            end_fmt = format_date(ev.get("end_date"))
            if start_fmt and end_fmt and start_fmt != end_fmt:
                dates = "dal {} al {}".format(start_fmt, end_fmt)
            elif start_fmt:
                dates = start_fmt
            else:
                dates = ""

            categories = ev.get("categories") or []
            category = categories[0].get("name") if categories else None

            events.append(
                {
                    "title": title,
                    "venue": venue,
                    "dates": dates,
                    "category": category,
                    "url": ev.get("url") or "",
                }
            )

        page += 1

    return events


def main():
    try:
        events = fetch_events()
    except Exception as exc:  # noqa: BLE001
        print(
            "Errore scaricando gli eventi culturali di Trieste: {}".format(exc),
            file=sys.stderr,
        )
        sys.exit(1)

    if not events:
        print(
            "Nessun evento culturale trovato per Trieste: possibile cambio "
            "della REST API di triestecultura.it.",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        payload = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        payload = {}

    payload["trieste_eventi"] = events
    payload["trieste_eventi_aggiornato_il"] = datetime.now().strftime(
        "%d %B %Y, %H:%M"
    )

    OUTPUT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("Aggiunti {} eventi culturali di Trieste a data.json.".format(len(events)))


if __name__ == "__main__":
    main()
