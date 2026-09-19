"""
Ricarica il calendario mostre di Trieste da arte.it e rigenera data.json.

Nota importante: questo script dipende dalla struttura HTML attuale di
arte.it. Se il sito cambia layout, i selettori qui sotto potrebbero
smettere di funzionare: in quel caso lo script termina senza scrivere
nulla di rotto (mantiene l'ultimo data.json valido) e stampa un avviso
nei log dell'Action.
"""

import json
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

OUTPUT_PATH = Path(__file__).resolve().parent.parent / "data.json"

# slug usato nell'URL arte.it -> nome citta' da mostrare
CITIES = [
    ("trieste", "Trieste"),
    ("udine", "Udine"),
    ("gorizia", "Gorizia"),
    ("pordenone", "Pordenone"),
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; mostre-fvg-bot/1.0; +https://github.com/)"
}

# Estrae dal testo concatenato di ogni link-mostra:
#   "{titolo} Dal {inizio} al {fine} {citta} | {sede} {titolo ripetuto} ..."
ENTRY_PATTERN = re.compile(
    r"^(?P<title>.+?)\s+Dal\s+(?P<start>\d{1,2}\s+\w+\s+\d{4})\s+al\s+"
    r"(?P<end>\d{1,2}\s+\w+\s+\d{4})\s+(?P<city>[\w'\s]+?)\s*\|\s*(?P<venue>.+?)\s+"
    r"(?P=title)",
    re.UNICODE,
)

ITALIAN_MONTHS = {
    "gennaio": 1, "febbraio": 2, "marzo": 3, "aprile": 4,
    "maggio": 5, "giugno": 6, "luglio": 7, "agosto": 8,
    "settembre": 9, "ottobre": 10, "novembre": 11, "dicembre": 12,
}


def parse_italian_date(text):
    """'27 Settembre 2026' -> date(2026, 9, 27). None se non riconosciuta."""
    m = re.match(r"(\d{1,2})\s+(\w+)\s+(\d{4})", text.strip())
    if not m:
        return None
    day, month_name, year = m.groups()
    month = ITALIAN_MONTHS.get(month_name.lower())
    if not month:
        return None
    try:
        return date(int(year), month, int(day))
    except ValueError:
        return None


def fetch_city_exhibitions(slug, city_name):
    url = "https://www.arte.it/calendario-arte/{}".format(slug)
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    today = date.today()
    results = []
    seen_urls = set()
    needle = "/calendario-arte/{}/mostra-".format(slug)

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if needle not in href or href in seen_urls:
            continue

        text = re.sub(r"\s+", " ", a.get_text(separator=" ", strip=True))
        match = ENTRY_PATTERN.match(text)
        if not match:
            continue

        title = match.group("title").strip()
        start_raw = match.group("start").strip()
        end_raw = match.group("end").strip()
        venue = match.group("venue").strip()
        city = match.group("city").strip()

        if city_name.lower() not in city.lower():
            continue

        # Scarta le mostre gia' chiuse. Se la data non si riesce a
        # interpretare, la mostra viene comunque inclusa per prudenza.
        end_date = parse_italian_date(end_raw)
        if end_date is not None and end_date < today:
            continue

        full_url = href if href.startswith("http") else "https://www.arte.it" + href

        results.append(
            {
                "title": title,
                "venue": venue,
                "dates": "dal {} al {}".format(start_raw, end_raw),
                "url": full_url,
            }
        )
        seen_urls.add(href)

    return results


def main():
    cities_payload = {}
    any_success = False
    failures = []

    for slug, city_name in CITIES:
        try:
            exhibitions = fetch_city_exhibitions(slug, city_name)
        except Exception as exc:  # noqa: BLE001
            print("Errore scraping {}: {}".format(city_name, exc), file=sys.stderr)
            failures.append(city_name)
            continue

        if not exhibitions:
            print(
                "Nessuna mostra trovata per {}: possibile cambio di struttura "
                "della pagina.".format(city_name),
                file=sys.stderr,
            )
            failures.append(city_name)
            continue

        cities_payload[slug] = {"city": city_name, "exhibitions": exhibitions}
        any_success = True

    if not any_success:
        print(
            "Nessuna citta' ha prodotto risultati: non aggiorno data.json.",
            file=sys.stderr,
        )
        sys.exit(1)

    payload = {
        "generated_at": datetime.now(timezone.utc)
        .astimezone()
        .strftime("%d %B %Y, %H:%M %Z"),
        "cities": cities_payload,
        "failed_cities": failures,
    }

    OUTPUT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    total = sum(len(c["exhibitions"]) for c in cities_payload.values())
    print("data.json aggiornato: {} mostre in {} citta'.".format(total, len(cities_payload)))

    if failures:
        # Segnala l'esito parziale senza far fallire tutta la run: il
        # workflow legge questo per aprire un'issue di avviso.
        print("::warning::Scraping fallito per: {}".format(", ".join(failures)))


if __name__ == "__main__":
    main()
