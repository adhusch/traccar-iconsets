#!/usr/bin/env python3
"""
Erzeugt taktische Zeichen (DV 102 / FwDV 100) als einfarbige SVG-Icons fuer
Traccar und traegt sie in iconsets/feuerwehr/iconset.json ein.

Traccar faerbt Marker-Icons in der Statusfarbe ein (gruen/rot/grau) und wertet
dabei nur den Alphakanal aus. Deshalb sind die Zeichen Silhouetten in einer
Farbe; Details sind Aussparungen. Beschriftungen werden als Pfad eingebettet,
damit keine Schriftart installiert sein muss.

Zeichenarten (alle 256x256, Geometrie nach jonas-koeritz/Taktische-Zeichen):

  Fahrzeug  oben Grundzeichen Fahrzeug, optional Fachdienstzeichen "Loeschen"
            (ausgesparter Pfeil); 2 Raeder = strassengaengig, 3 = gelaendegaengig
            unten eine Zeile Beschriftung (Literzahl oder Kurzbezeichnung)
  Person    Raute als Ring, obere Spitze ausgemalt = Fuehrer,
            Punkte darueber = Groessenordnung (1 Trupp, 2 Gruppe, 3 Zug)

Aufruf:   python3 tools/generate.py            alle Icons erzeugen
          python3 tools/generate.py lf10 elw   nur diese

Danach in Portainer den Container "traccar-iconsets" starten und den Browser
neu laden. Voraussetzung: Python 3 mit fonttools (pip install fonttools) und
die Schrift DejaVu Sans Condensed Bold (oder --font <pfad.ttf>).
"""

import argparse
import datetime
import json
import sys
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "iconsets" / "feuerwehr"
MANIFEST = OUT / "iconset.json"

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf",
    "/usr/share/fonts/dejavu/DejaVuSansCondensed-Bold.ttf",
    "/Library/Fonts/DejaVuSansCondensed-Bold.ttf",
    str(Path.home() / "Library/Fonts/DejaVuSansCondensed-Bold.ttf"),
    "C:/Windows/Fonts/DejaVuSansCondensed-Bold.ttf",
]

# ============================================================================
# Icon-Liste – hier neue Zeichen eintragen
# ============================================================================

# Fahrzeuge: (id, Beschriftung im Icon, Raeder 2|3, Loeschen-Zeichen, Name)
#   id          Kategoriename, nur a-z 0-9 _ -, wird so am Geraet gespeichert
#   Beschriftung  Literzahl bei Tankfahrzeugen, sonst Kurzbezeichnung (<= 5 Zeichen)
#   Name        Text im Auswahlfeld von Traccar
VEHICLES = [
    # strassengaengig -> 2 Raeder
    ("lf10",      "600",   2, True,  "LF 10/6 (600 l)"),
    ("hlf10",     "1000",  2, True,  "HLF 10 (1000 l)"),
    ("tlf1625",   "2500",  2, True,  "TLF 16/25 (2500 l)"),
    ("gtlf",      "15000", 2, True,  "GTLF 15000"),
    ("tsfw750",   "750",   2, True,  "TSF-W (750 l)"),
    ("tsfw500",   "500",   2, True,  "TSF-W (500 l)"),
    ("tsf",       "TSF",   2, True,  "TSF"),
    ("klf",       "KLF",   2, True,  "KLF"),
    ("elw",       "ELW",   2, False, "ELW"),
    ("kdow",      "KdoW",  2, False, "KdoW"),
    ("mzf1",      "MZF 1", 2, False, "MZF 1"),
    ("mzf2",      "MZF 2", 2, False, "MZF 2"),
    # gelaendegaengig -> 3 Raeder
    ("tsfw750gg", "750",   3, True,  "TSF-W 4x4 (750 l)"),
    ("tsfw500gg", "500",   3, True,  "TSF-W 4x4 (500 l)"),
    ("utv",       "UTV",   3, False, "UTV (geländegängig)"),
]

# Fuehrungskraefte: (id, Punkte 1|2|3, Name)
PERSONS = [
    ("gruppenfuehrer", 2, "Gruppenführer"),
    ("zugfuehrer",     3, "Zugführer"),
]

# ============================================================================
# Geometrie
# ============================================================================

# Grundzeichen Fahrzeug (Originalkoordinaten des DV-102-Zeichensatzes)
BODY = "M10,64 L10,192 L246,192 L246,64 Q128,100 10,64 Z"
WHEEL_CY, WHEEL_R = 212, 15
WHEELS = {2: (40, 216), 3: (40, 128, 216)}
# Fachdienstzeichen "Loeschen" (Brandbekaempfung), als Aussparung
LOESCHEN = "M30,128 L228,128 M146,128 L216,170 M146,128 L216,86"
LOESCHEN_W = 20
# Zeichenblock oben einpassen: y 64..227 -> 4..175, x 10..246 -> 4..251
SIGN_TRANSFORM = "translate(-6.5,-63.2) scale(1.05)"

# Beschriftung unter dem Fahrzeug
BASELINE = 246.0
CAP_HEIGHT = 60.0
MAX_WIDTH = 244.0
CENTER_X = 128.0

# Grundzeichen Person: Raute + ausgemalte Spitze + Groessenordnungspunkte,
# auf die volle Hoehe skaliert (y 34..192 -> 6..250)
RAUTE = "M64,128 L128,64 L192,128 L128,192 Z"
SPITZE = "M128,64 L152,88 L104,88 Z"
RAUTE_W = 13
DOTS = {1: (128,), 2: (100, 156), 3: (100, 128, 156)}
DOT_CY, DOT_R = 44, 10
PERSON_TRANSFORM = "translate(-69.6,-46.5) scale(1.544)"


def find_font(explicit: str | None) -> str:
    for candidate in ([explicit] if explicit else []) + FONT_CANDIDATES:
        if candidate and Path(candidate).exists():
            return candidate
    sys.exit(
        "Schrift DejaVu Sans Condensed Bold nicht gefunden.\n"
        "Installieren (Linux: Paket fonts-dejavu-core) oder mit --font <pfad.ttf> angeben."
    )


def text_path(label: str, font_path: str) -> str:
    """Setzt den Text und gibt ihn als SVG-Pfad in Icon-Koordinaten zurueck."""
    font = TTFont(font_path)
    glyph_set = font.getGlyphSet()
    cmap = font.getBestCmap()
    hmtx = font["hmtx"]
    # Versalhoehe aus dem "H" messen (sCapHeight fehlt in manchen Fonts)
    cap = font["glyf"][cmap[ord("H")]].yMax

    parts, pen_x = [], 0
    for char in label:
        name = cmap.get(ord(char))
        if name is None:
            continue
        pen = SVGPathPen(glyph_set)
        glyph_set[name].draw(pen)
        d = pen.getCommands()
        if d:
            parts.append(f'<path transform="translate({pen_x},0)" d="{d}"/>')
        pen_x += hmtx[name][0]

    scale = CAP_HEIGHT / cap
    if pen_x * scale > MAX_WIDTH:  # zu breit -> proportional verkleinern
        scale = MAX_WIDTH / pen_x
    tx = CENTER_X - (pen_x * scale) / 2

    # y spiegeln: Schrift-y zeigt nach oben, SVG-y nach unten
    return (
        f'<g transform="translate({tx:.2f},{BASELINE}) scale({scale:.5f},{-scale:.5f})">'
        + "".join(parts)
        + "</g>"
    )


def vehicle_svg(label: str, wheels: int, loeschen: bool, title: str, font: str) -> str:
    mask, body_attr = "", ""
    if loeschen:
        mask = f"""  <defs>
    <mask id="fd" maskUnits="userSpaceOnUse" x="0" y="0" width="256" height="256">
      <rect x="0" y="0" width="256" height="256" fill="#ffffff"/>
      <path d="{LOESCHEN}" fill="none" stroke="#000000"
            stroke-width="{LOESCHEN_W}" stroke-linecap="round"/>
    </mask>
  </defs>
"""
        body_attr = ' mask="url(#fd)"'

    dots = "\n    ".join(
        f'<circle cx="{cx}" cy="{WHEEL_CY}" r="{WHEEL_R}"/>' for cx in WHEELS[wheels]
    )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256" viewBox="0 0 256 256">
  <title>{title}</title>
{mask}  <g transform="{SIGN_TRANSFORM}" fill="#000000">
    <path d="{BODY}"{body_attr}/>
    {dots}
  </g>
  <g fill="#000000">{text_path(label, font)}</g>
</svg>
"""


def person_svg(dots: int, title: str) -> str:
    circles = "\n    ".join(
        f'<circle cx="{cx}" cy="{DOT_CY}" r="{DOT_R}"/>' for cx in DOTS[dots]
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256" viewBox="0 0 256 256">
  <title>{title}</title>
  <g transform="{PERSON_TRANSFORM}" fill="#000000">
    <path d="{RAUTE}"
          fill="none" stroke="#000000" stroke-width="{RAUTE_W}" stroke-linejoin="miter"/>
    <path d="{SPITZE}"/>
    {circles}
  </g>
</svg>
"""


def ascii_title(text: str) -> str:
    """SVG-Titel ohne Umlaute, damit die Dateien in jedem Editor sauber bleiben."""
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("Ä", "Ae"), ("Ö", "Oe"),
                 ("Ü", "Ue"), ("ß", "ss")):
        text = text.replace(a, b)
    return text


def update_manifest(entries: list[tuple[str, str]]) -> None:
    """
    Traegt die erzeugten Icons in iconset.json ein und zaehlt "version" hoch.
    Von Hand ergaenzte Eintraege bleiben erhalten; die Reihenfolge der
    generierten Icons folgt den Listen oben.
    """
    manifest = (
        json.loads(MANIFEST.read_text(encoding="utf-8"))
        if MANIFEST.exists()
        else {"name": "Taktische Zeichen Feuerwehr (DV 102 / FwDV 100)", "icons": []}
    )
    generated = {icon_id for icon_id, _ in entries}
    existing = {icon["id"]: icon for icon in manifest.get("icons", [])}

    icons = [{"id": i, "file": f"{i}.svg", "name": n} for i, n in entries]
    icons += [icon for icon_id, icon in existing.items() if icon_id not in generated]
    manifest["icons"] = icons

    # Neue version -> Browser laden die Icons frisch statt aus dem Cache
    manifest["version"] = datetime.datetime.now().strftime("%Y-%m-%d-%H%M")
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("ids", nargs="*", help="nur diese Icons erzeugen")
    parser.add_argument("--font", help="Pfad zu DejaVuSansCondensed-Bold.ttf")
    args = parser.parse_args()

    all_ids = [v[0] for v in VEHICLES] + [p[0] for p in PERSONS]
    unknown = set(args.ids) - set(all_ids)
    if unknown:
        sys.exit(f"Unbekannte ids: {', '.join(sorted(unknown))}")
    if len(all_ids) != len(set(all_ids)):
        sys.exit("Doppelte ids in VEHICLES/PERSONS")
    wanted = set(args.ids) or set(all_ids)

    font = find_font(args.font)
    OUT.mkdir(parents=True, exist_ok=True)

    for icon_id, label, wheels, loeschen, name in VEHICLES:
        if icon_id in wanted:
            svg = vehicle_svg(label, wheels, loeschen, ascii_title(name), font)
            (OUT / f"{icon_id}.svg").write_text(svg)
            print(f"  {icon_id}.svg  [{label}]  {wheels} Raeder{'  +Loeschen' if loeschen else ''}")

    for icon_id, dots, name in PERSONS:
        if icon_id in wanted:
            (OUT / f"{icon_id}.svg").write_text(person_svg(dots, ascii_title(name)))
            print(f"  {icon_id}.svg  Raute, {dots} Punkt(e)")

    update_manifest([(v[0], v[4]) for v in VEHICLES] + [(p[0], p[2]) for p in PERSONS])
    print(f"\n  {MANIFEST.relative_to(ROOT)} aktualisiert")


if __name__ == "__main__":
    main()
