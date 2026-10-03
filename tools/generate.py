#!/usr/bin/env python3
"""
Erzeugt taktische Zeichen (DV 102 / FwDV 100) als einfarbige SVG-Icons fuer
Traccar und traegt sie in iconsets/feuerwehr/iconset.json ein.

Traccar faerbt Marker-Icons in der Statusfarbe ein (gruen/rot/grau) und wertet
dabei nur den Alphakanal aus. Deshalb sind die Zeichen Silhouetten in einer
Farbe; Details sind Aussparungen. Beschriftungen werden als Pfad eingebettet,
damit keine Schriftart installiert sein muss.

Zeichenarten (alle 256x256, Geometrie nach jonas-koeritz/Taktische-Zeichen):

  Fahrzeug  oben eine Zeile Beschriftung (Literzahl oder Kurzbezeichnung),
            darunter Grundzeichen Fahrzeug, optional Fachdienstzeichen "Loeschen"
            (ausgesparte Linie von links, die sich zu den rechten Ecken
            verzweigt = Verteiler); 2 Raeder = strassengaengig, 3 = gelaendegaengig;
            optional Zusatzzeichen Gebirge (ausgefuelltes Dreieck, angelehnt an
            das militaerische Zeichen fuer Gebirgstruppen)
  Person    Raute als Ring, obere Spitze ausgemalt = Fuehrer (ohne Spitze =
            Truppmann), darueber Punkte/Striche = Groessenordnung
            (1 Punkt Trupp, 2 Gruppe, 3 Zug, 1 Strich Verband);
            Wehrleiter = Verbandsfuehrer mit Kuerzel "WL" in der Raute

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

# Fahrzeuge: (id, Beschriftung im Icon, Raeder 2|3, Loeschen-Zeichen, Gebirge, Name)
#   id          Kategoriename, nur a-z 0-9 _ -, wird so am Geraet gespeichert
#   Beschriftung  Literzahl bei Tankfahrzeugen, sonst Kurzbezeichnung (<= 5 Zeichen);
#               steht ueber dem Zeichen
#   Gebirge     Zusatzzeichen Gebirgstruppe (Absturzsicherung / Mittelgebirgsrettung)
#   Name        Text im Auswahlfeld von Traccar
VEHICLES = [
    # strassengaengig -> 2 Raeder
    ("lf10",      "600",   2, True,  False, "LF 10/6 (600 l)"),
    ("hlf10",     "1000",  2, True,  False, "HLF 10 (1000 l)"),
    ("tlf1625",   "2500",  2, True,  False, "TLF 16/25 (2500 l)"),
    ("gtlf",      "15000", 2, True,  False, "GTLF 15000"),
    ("tsfw750",   "750",   2, True,  False, "TSF-W (750 l)"),
    ("tsfw500",   "500",   2, True,  False, "TSF-W (500 l)"),
    ("tsf",       "TSF",   2, True,  False, "TSF"),
    ("klf",       "KLF",   2, True,  False, "KLF"),
    ("elw",       "ELW",   2, False, False, "ELW"),
    ("kdow",      "KdoW",  2, False, False, "KdoW"),
    ("mzf1",      "MZF 1", 2, False, False, "MZF 1"),
    ("mzf2",      "MZF 2", 2, False, False, "MZF 2"),
    # gelaendegaengig -> 3 Raeder
    ("tsfw750gg", "750",   3, True,  False, "TSF-W 4x4 (750 l)"),
    ("tsfw500gg", "500",   3, True,  False, "TSF-W 4x4 (500 l)"),
    ("utv",       "UTV",   3, False, False, "UTV (geländegängig)"),
    # Absturzsicherung / Mittelgebirgsrettung -> Zusatzzeichen Gebirge
    ("tsfw500_abstusi",   "500", 2, True,  True, "TSF-W (500 l) AbStuSi"),
    ("tsf_abstusi",       "TSF", 2, True,  True, "TSF AbStuSi"),
    ("tsfw750gg_abstusi", "750", 3, True,  True, "TSF-W 4x4 (750 l) AbStuSi"),
    ("utv_abstusi",       "UTV", 3, False, True, "UTV AbStuSi (geländegängig)"),
]

# Fuehrungskraefte: (id, Fuehrer-Spitze, Groessenordnung, Text in der Raute, Name)
#   Groessenordnung: "" nichts, "." Punkt, "|" Strich (Reihenfolge = Anzeige)
#   Text in der Raute: "" nichts, sonst kurzes Kuerzel (z. B. "WL")
PERSONS = [
    ("truppmann",       False, "",    "",   "Truppmann"),
    ("truppfuehrer",    True,  ".",   "",   "Truppführer"),
    ("gruppenfuehrer",  True,  "..",  "",   "Gruppenführer"),
    ("zugfuehrer",      True,  "...", "",   "Zugführer"),
    ("verbandsfuehrer", True,  "|",   "",   "Verbandsführer"),
    ("wehrleiter",      True,  "|",   "WL", "Wehrleiter"),
]

# ============================================================================
# Geometrie
# ============================================================================

# Grundzeichen Fahrzeug (Originalkoordinaten des DV-102-Zeichensatzes)
BODY = "M10,64 L10,192 L246,192 L246,64 Q128,100 10,64 Z"
WHEEL_CY, WHEEL_R = 212, 15
WHEELS = {2: (40, 216), 3: (40, 128, 216)}
# Fachdienstzeichen "Loeschen" (Brandbekaempfung, Verteiler), als Aussparung:
# Linie von der linken Kante, ab BRANCH_X teilt sie sich in drei Linien, die bis
# in die rechte obere/untere Ecke und die rechte Kante reichen. Die Linien sind
# ueber den Rand verlaengert, damit sie das Zeichen sauber durchtrennen.
BODY_L, BODY_R, BODY_T, BODY_B = 10, 246, 64, 192
BODY_MID = (BODY_T + BODY_B) / 2
BRANCH_X = 164
LOESCHEN_W = 20
EXTEND = 1.15  # Diagonalen ueber die Ecke hinaus verlaengern


def _loeschen_path() -> str:
    dx, dy = BODY_R - BRANCH_X, BODY_T - BODY_MID
    x2, y_up = BRANCH_X + dx * EXTEND, BODY_MID + dy * EXTEND
    y_dn = BODY_MID - dy * EXTEND
    return (f"M{BODY_L - 10},{BODY_MID:g} L{BODY_R + 10},{BODY_MID:g} "
            f"M{BRANCH_X},{BODY_MID:g} L{x2:.1f},{y_up:.1f} "
            f"M{BRANCH_X},{BODY_MID:g} L{x2:.1f},{y_dn:.1f}")


LOESCHEN = _loeschen_path()

# Zusatzzeichen Gebirge (Gebirgstruppe): ausgefuelltes Dreieck als Aussparung, in
# allen Fahrzeugen mittig. Bei Loeschen liegt es unter der Linie links der
# Verzweigung, beim Fahrzeug ohne Loeschen-Zeichen an derselben Stelle.
GEBIRGE_CX, GEBIRGE_BASE = 128, 184
GEBIRGE_HALF, GEBIRGE_H = 26, 40


def _gebirge_path() -> str:
    cx, base = GEBIRGE_CX, GEBIRGE_BASE
    return (f"M{cx - GEBIRGE_HALF},{base} L{cx},{base - GEBIRGE_H} "
            f"L{cx + GEBIRGE_HALF},{base} Z")


# Zeichenblock unter die Beschriftung setzen: y 64..227 -> 82..253, x 10..246 -> 4..251
SIGN_TRANSFORM = "translate(-6.5,14.8) scale(1.05)"

# Beschriftung ueber dem Fahrzeug
BASELINE = 66.0
CAP_HEIGHT = 60.0
MAX_WIDTH = 244.0
CENTER_X = 128.0

# Grundzeichen Person: Raute + ausgemalte Spitze + Groessenordnung (Punkte/Striche),
# auf die volle Hoehe skaliert (y 24..192 -> 6..250)
RAUTE = "M64,128 L128,64 L192,128 L128,192 Z"
SPITZE = "M128,64 L152,88 L104,88 Z"
RAUTE_W = 13
MARK_PITCH = 28           # Abstand der Punkte/Striche
DOT_CY, DOT_R = 38, 10
BAR_Y0, BAR_Y1, BAR_W = 24, 48, 12
PERSON_SCALE, PERSON_TX, PERSON_TY = 1.45, -57.6, -28.8
PERSON_TRANSFORM = f"translate({PERSON_TX},{PERSON_TY}) scale({PERSON_SCALE})"
# Kuerzel in der Raute (Icon-Koordinaten): Breite + Hoehe <= ca. 150
TEXT_CAP, TEXT_MAX_W = 52.0, 96.0


def find_font(explicit: str | None) -> str:
    for candidate in ([explicit] if explicit else []) + FONT_CANDIDATES:
        if candidate and Path(candidate).exists():
            return candidate
    sys.exit(
        "Schrift DejaVu Sans Condensed Bold nicht gefunden.\n"
        "Installieren (Linux: Paket fonts-dejavu-core) oder mit --font <pfad.ttf> angeben."
    )


def text_path(label: str, font_path: str, baseline: float = BASELINE,
              cap_height: float = CAP_HEIGHT, max_width: float = MAX_WIDTH,
              center_x: float = CENTER_X) -> str:
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

    scale = cap_height / cap
    if pen_x * scale > max_width:  # zu breit -> proportional verkleinern
        scale = max_width / pen_x
    tx = center_x - (pen_x * scale) / 2

    # y spiegeln: Schrift-y zeigt nach oben, SVG-y nach unten
    return (
        f'<g transform="translate({tx:.2f},{baseline}) scale({scale:.5f},{-scale:.5f})">'
        + "".join(parts)
        + "</g>"
    )


def vehicle_svg(label: str, wheels: int, loeschen: bool, gebirge: bool,
                title: str, font: str) -> str:
    strokes = []
    if loeschen:
        strokes.append(f'<path d="{LOESCHEN}" fill="none" stroke="#000000" '
                       f'stroke-width="{LOESCHEN_W}"/>')
    if gebirge:
        strokes.append(f'<path d="{_gebirge_path()}" fill="#000000"/>')
    mask, body_attr = "", ""
    if strokes:
        mask = f"""  <defs>
    <mask id="fd" maskUnits="userSpaceOnUse" x="0" y="0" width="256" height="256">
      <rect x="0" y="0" width="256" height="256" fill="#ffffff"/>
      {chr(10).join("      " + t for t in strokes).strip()}
    </mask>
  </defs>
"""
        body_attr = ' mask="url(#fd)"'

    dots = "\n    ".join(
        f'<circle cx="{cx}" cy="{WHEEL_CY}" r="{WHEEL_R}"/>' for cx in WHEELS[wheels]
    )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256" viewBox="0 0 256 256">
  <title>{title}</title>
{mask}  <g fill="#000000">{text_path(label, font)}</g>
  <g transform="{SIGN_TRANSFORM}" fill="#000000">
    <path d="{BODY}"{body_attr}/>
    {dots}
  </g>
</svg>
"""


def person_svg(spitze: bool, marks: str, text: str, title: str, font: str) -> str:
    """marks: "." = Punkt, "|" = Strich; zentriert ueber der Raute."""
    xs = [128 + (i - (len(marks) - 1) / 2) * MARK_PITCH for i in range(len(marks))]
    shapes = "\n    ".join(
        f'<circle cx="{x:g}" cy="{DOT_CY}" r="{DOT_R}"/>' if m == "."
        else f'<rect x="{x - BAR_W / 2:g}" y="{BAR_Y0}" width="{BAR_W}" height="{BAR_Y1 - BAR_Y0}"/>'
        for x, m in zip(xs, marks)
    )
    tip = f'\n    <path d="{SPITZE}"/>' if spitze else ""
    # Kuerzel mittig in der Raute (Raute-Mitte 128,128 in Zeichenkoordinaten)
    label = ""
    if text:
        cy = 128 * PERSON_SCALE + PERSON_TY
        label = ("\n  <g fill=\"#000000\">"
                 + text_path(text, font, baseline=cy + TEXT_CAP / 2, cap_height=TEXT_CAP,
                             max_width=TEXT_MAX_W, center_x=128.0)
                 + "</g>")
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256" viewBox="0 0 256 256">
  <title>{title}</title>
  <g transform="{PERSON_TRANSFORM}" fill="#000000">
    <path d="{RAUTE}"
          fill="none" stroke="#000000" stroke-width="{RAUTE_W}" stroke-linejoin="miter"/>{tip}
    {shapes}
  </g>{label}
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

    for icon_id, label, wheels, loeschen, gebirge, name in VEHICLES:
        if icon_id in wanted:
            svg = vehicle_svg(label, wheels, loeschen, gebirge, ascii_title(name), font)
            (OUT / f"{icon_id}.svg").write_text(svg)
            extras = ("  +Loeschen" if loeschen else "") + ("  +Gebirge" if gebirge else "")
            print(f"  {icon_id}.svg  [{label}]  {wheels} Raeder{extras}")

    for icon_id, spitze, marks, text, name in PERSONS:
        if icon_id in wanted:
            (OUT / f"{icon_id}.svg").write_text(person_svg(spitze, marks, text, ascii_title(name), font))
            print(f"  {icon_id}.svg  Raute{' + Spitze' if spitze else ''}  [{marks}] {text}")

    update_manifest([(v[0], v[5]) for v in VEHICLES] + [(p[0], p[4]) for p in PERSONS])
    print(f"\n  {MANIFEST.relative_to(ROOT)} aktualisiert")


if __name__ == "__main__":
    main()
