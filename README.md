# Mostre a Trieste e FVG

Pagina statica con tab per Trieste, Udine, Gorizia e Pordenone, ciascuna
con l'elenco delle mostre attualmente aperte. I dati vengono ricaricati
automaticamente da arte.it una volta al giorno tramite GitHub Actions.
Le mostre già chiuse vengono escluse automaticamente.

## Come funziona

- `index.html` — la pagina: all'apertura legge `data.json` (nello
  stesso repository) e costruisce un tab per ogni città. Nessuna
  chiamata a siti esterni dal browser: evita i blocchi di sicurezza
  (CORS) che impedirebbero a una pagina statica di leggere direttamente
  arte.it. Può anche essere aggiunta alla home screen come app grazie a
  `manifest.json`.
- `data.json` — lo "snapshot" dei dati, con `generated_at` (data
  dell'ultimo aggiornamento) e `failed_cities` (città per cui
  l'ultimo scraping non ha trovato nulla, se presenti).
- `scripts/scrape.py` — script Python che ricarica le pagine di
  Trieste, Udine, Gorizia e Pordenone su arte.it, scarta le mostre già
  concluse e rigenera `data.json`.
- `.github/workflows/update.yml` — un'azione schedulata che esegue lo
  scraper ogni giorno alle 05:00 UTC e fa il commit di `data.json` se è
  cambiato. Se lo scraping fallisce per tutte le città, apre
  automaticamente una issue nel repo per avvisarti. Puoi anche
  lanciarla a mano dalla tab "Actions" del repo ("Run workflow").

## Pubblicazione su GitHub Pages

1. Crea un repository su GitHub e carica tutti questi file (mantenendo
   la struttura delle cartelle, incluso `.github/workflows/`).
2. Vai su **Settings → Pages** e imposta come sorgente il branch
   principale (es. `main`), cartella `/ (root)`.
3. Vai su **Settings → Actions → General** e assicurati che i workflow
   abbiano permesso di scrittura ("Read and write permissions"), così
   l'Action può fare commit di `data.json`.
4. Dopo il primo giro dell'Action (automatico entro 24h, oppure lanciato
   a mano da "Actions → Aggiorna calendario mostre → Run workflow"), la
   pagina mostrerà i dati aggiornati.

## Limite noto

Lo scraper si basa sulla struttura HTML attuale di arte.it (cerca i
link `/calendario-arte/trieste/mostra-...` e ne interpreta il testo).
Se arte.it cambia il layout della pagina, lo script potrebbe non
trovare più mostre: in quel caso si ferma senza sovrascrivere
`data.json` e lo segnala nei log dell'Action ("Actions" → run fallito).
In tal caso i selettori in `scripts/scrape.py` vanno aggiornati.
