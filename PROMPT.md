# Start-Prompt für neue Icons

Diesen Text in einen neuen Chat kopieren und unten die gewünschten Zeichen
eintragen. Der Chat braucht GitHub-Zugriff auf `adhusch/traccar-iconsets`.
Ohne Zugriff stattdessen `tools/generate.py` und
`iconsets/feuerwehr/iconset.json` als Datei anhängen.

---

Ich betreibe Traccar mit eigenen Karten-Icons und brauche weitere taktische
Zeichen für meine Feuerwehr.

**Aufbau, der schon läuft – bitte nichts davon umbauen:**

- Weboberfläche aus `adhusch/traccar-web`: liest beim Start
  `/override/iconsets/index.json` und meldet die Icons der dort gelisteten Sets
  als Gerätekategorien an. Ein Neubau der App ist für neue Icons nicht nötig.
- Server-Image `ghcr.io/adhusch/traccar:<version>` aus `adhusch/traccar`
  (Workflow „Build Docker Image").
- Icons liegen im Repo `adhusch/traccar-iconsets` unter
  `iconsets/feuerwehr/`. In meinem Portainer-Stack klont der Container
  `traccar-iconsets` das Repo nach `/opt/traccar/override/iconsets`.
- `tools/generate.py` erzeugt alle Zeichen und pflegt `iconset.json`
  (inklusive `version` als Cache-Buster). Neue Zeichen kommen als Zeile in die
  Listen `VEHICLES` oder `PERSONS` am Anfang der Datei.

**Regeln für die Zeichen** (aus Erfahrung, bitte einhalten):

- Traccar färbt Icons in der Statusfarbe ein und nutzt nur den Alphakanal.
  Zeichen sind daher einfarbige Silhouetten, Details sind Aussparungen.
  Eigenfarben (rot/weiß nach DV 102) gehen verloren.
- Geometrie nach DV 102 / FwDV 100 bzw. `jonas-koeritz/Taktische-Zeichen`:
  - Fahrzeug: Grundzeichen mit durchhängender Oberkante.
    **2 Räder = straßengängig, 3 Räder = geländegängig.** Nicht raten – im
    Zweifel nachfragen, welche Fahrzeuge Allrad haben.
  - Fachdienstzeichen „Löschen" (ausgesparter Verteiler: Linie von links, die
    sich in drei Linien bis in die rechten Ecken und die rechte Kante teilt)
    für alle Löschfahrzeuge, auch ohne Tank (TSF, KLF).
  - Zusatzzeichen Gebirge (ausgefülltes Dreieck, nach dem militärischen
    Zeichen für Gebirgstruppen) für Fahrzeuge der Absturzsicherung
    (`AbStuSi`, Name mit „AbStuSi", id mit Suffix `_abstusi`).
  - Führungskraft: Raute als Ring, obere Spitze ausgemalt (Truppmann ohne
    Spitze), Punkte/Striche darüber für die Größenordnung (1 Trupp,
    2 Gruppe, 3 Zug, 1 Strich Verband; Wehrleiter = Verbandsführer mit „WL“ in der Raute).
- Über dem Fahrzeug steht genau eine Zeile: bei Tankfahrzeugen die
  Literzahl, sonst die Kurzbezeichnung. Höchstens etwa 5 Zeichen, sonst wird
  sie im Marker unlesbar.
- `id` nur aus Kleinbuchstaben, Ziffern, `_`, `-` – sie wird so am Gerät
  gespeichert und darf sich später nicht mehr ändern.
- Vor dem Abgeben die Icons so rendern, wie Traccar sie zeigt (64-px-Marker,
  Icon auf 50 %, in Statusfarbe eingefärbt), und mir eine Vorschau zeigen.

**Ablauf:**

1. Zeichen in `tools/generate.py` eintragen, `python3 tools/generate.py`
   ausführen.
2. Vorschau rendern und mir zeigen.
3. Commit und Push auf `main` von `adhusch/traccar-iconsets`.
4. Mir sagen: In Portainer den Container `traccar-iconsets` starten, dann im
   Browser neu laden.

**Neue Zeichen:**

| Fahrzeug / Funktion | Tank (Liter) | geländegängig? | Gebirge (AbStuSi)? | Beschriftung im Auswahlfeld |
|---|---|---|---|---|
| z. B. DLK 23/12 | – | nein | nein | DLK 23/12 |
| | | | | |

---

## Für mich: was bei Problemen hilft

- **Icons erscheinen nicht:** `https://<traccar>/override/iconsets/index.json`
  im Browser aufrufen. Kommt JSON, liegt es am Browser-Cache: Traccar ist eine
  PWA. Im privaten Fenster testen oder F12 → Application → Service Workers →
  Unregister, alle Traccar-Tabs schließen.
- **Altes Icon trotz Änderung:** `version` in `iconset.json` muss sich ändern
  (macht der Generator automatisch).
- **Traccar-Update:** im Fork `adhusch/traccar-web` upstream mergen, dann in
  `adhusch/traccar` den Workflow „Build Docker Image" mit der neuen Version
  starten. Die Icons sind davon nicht betroffen.
