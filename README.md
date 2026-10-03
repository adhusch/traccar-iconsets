# Traccar-Iconsets

Zusätzliche Karten-Icons für die Traccar-Oberfläche aus
[adhusch/traccar-web](https://github.com/adhusch/traccar-web). Die Oberfläche liest
sie zur Laufzeit aus dem Override-Ordner des Servers (`/opt/traccar/override`) –
ein Neubau ist für neue Icons nicht nötig.

## Inhalt

```
iconsets/
├── index.json              welche Sets geladen werden, Markergröße
└── feuerwehr/
    ├── iconset.json        Icons mit Beschriftung
    └── *.svg               taktische Zeichen nach DV 102 / FwDV 100
tools/
└── generate.py             erzeugt die Feuerwehr-Zeichen und pflegt iconset.json
PROMPT.md                   Start-Prompt für einen neuen Chat, um Zeichen zu ergänzen
```

## Einbindung in Portainer

Ein Hilfscontainer klont dieses Repo beim Start in ein Volume, Traccar hängt es
schreibgeschützt ein:

```yaml
services:
  iconsets:
    image: alpine/git
    restart: "no"
    entrypoint: ["/bin/sh", "-c"]
    command:
      - |
        set -e
        rm -rf /tmp/src
        git clone --depth 1 https://github.com/adhusch/traccar-iconsets /tmp/src
        rm -rf /override/iconsets
        cp -r /tmp/src/iconsets /override/iconsets
        echo "Iconsets aktualisiert"
    volumes:
      - traccar-override:/override

  traccar:
    image: ghcr.io/adhusch/traccar:6.16.0-alpine
    depends_on:
      - iconsets
    volumes:
      - traccar-override:/opt/traccar/override:ro
      # ... übrige Volumes

volumes:
  traccar-override:
```

## Icons ändern oder ergänzen

1. SVG in `iconsets/<set>/` ablegen und in `iconset.json` eintragen:
   `{ "id": "dlk23", "file": "dlk23.svg", "name": "DLK 23/12" }`
2. Beim **Ersetzen** einer bestehenden Datei `version` in `iconset.json`
   hochzählen, sonst zeigt der Browser das alte Bild aus dem Cache.
3. In Portainer den Container `iconsets` einmal starten, im Browser neu laden.

Ein weiteres Set ist ein neuer Ordner plus Eintrag unter `sets` in `index.json`.

### Regeln für Icons

- `id` nur aus `A-Z a-z 0-9 _ -`; sie wird so am Gerät gespeichert.
- Einfarbige SVGs mit `width`, `height` und `viewBox`. Traccar färbt Icons in der
  Statusfarbe ein und nutzt dabei nur den Alphakanal – Details als Aussparung
  zeichnen, Eigenfarben gehen verloren.
- Eine `id` einer eingebauten Kategorie (z. B. `car`) ersetzt deren Icon.

### Neue Feuerwehr-Zeichen erzeugen

`tools/generate.py` (Python 3 mit `fonttools`, Schrift DejaVu Sans Condensed
Bold) baut alle Zeichen im einheitlichen Stil und trägt sie in `iconset.json`
ein – inklusive neuer `version`. Von Hand ergänzte Einträge bleiben erhalten.

- Fahrzeug: Zeile in `VEHICLES` – id, Beschriftung (steht über dem Zeichen), Räder (2/3),
  Löschen ja/nein, Gebirge ja/nein (Zusatzzeichen Gebirgstruppe, z. B. für
  Absturzsicherung), Name
- Führungskraft: Zeile in `PERSONS` – id, ausgemalte Spitze ja/nein, Größenordnung
  (`.` Punkt, `|` Strich: 1 Trupp, 2 Gruppe, 3 Zug, 1 Strich Verband), Kürzel in der Raute (z. B. `WL`), Name

```sh
pip install fonttools
python3 tools/generate.py            # alle
python3 tools/generate.py dlk23      # nur dieses
```

Für einen neuen Chat liegt in `PROMPT.md` ein fertiger Start-Prompt.

## Quelle der Zeichen

Geometrie nach dem Zeichensatz
[jonas-koeritz/Taktische-Zeichen](https://github.com/jonas-koeritz/Taktische-Zeichen)
(CC BY 4.0).
