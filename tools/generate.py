#!/usr/bin/env python3
"""
Erzeugt taktische Zeichen (DV 102 / FwDV 100) als einfarbige SVG-Icons fuer Traccar.

Traccar faerbt Marker-Icons in der Statusfarbe ein (nur der Alphakanal bleibt
erhalten), deshalb sind die Zeichen als Silhouette mit ausgesparten Details
gezeichnet. Die Beschriftung wird als Pfad eingebettet (keine Font-Abhaengigkeit).

Aufbau je Icon (256x256):
  oben   Grundzeichen Fahrzeug + ggf. Fachdienstzeichen "Loeschen" (ausgespart)
         2 Raeder = strassengaengig, 3 Raeder = gelaendegaengig
  unten  Kurzbezeichnung bzw. Loeschwassermenge in Litern
"""

from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf"
OUT = Path(__file__).resolve().parent.parent / "iconsets" / "feuerwehr"

# --- Grundzeichen Fahrzeug (Originalkoordinaten des DV-102-Zeichensatzes) ---
BODY = "M10,64 L10,192 L246,192 L246,64 Q128,100 10,64 Z"
WHEEL_CY, WHEEL_R = 212, 15
WHEELS = {2: (40, 216), 3: (40, 128, 216)}
# Fachdienstzeichen "Loeschen" (Brandbekaempfung), als Aussparung
LOESCHEN = "M30,128 L228,128 M146,128 L216,170 M146,128 L216,86"
LOESCHEN_W = 20
# Zeichenblock oben einpassen: y 64..227 -> 4..175, x 10..246 -> 4..251
SIGN_TRANSFORM = "translate(-6.5,-63.2) scale(1.05)"

# --- Beschriftung ---
BASELINE = 246.0
CAP_HEIGHT = 60.0
MAX_WIDTH = 244.0
CENTER_X = 128.0


def text_path(label: str) -> str:
    """Setzt den Text und gibt ihn als SVG-Pfad in Icon-Koordinaten zurueck."""
    font = TTFont(FONT)
    glyph_set = font.getGlyphSet()
    cmap = font.getBestCmap()
    hmtx = font["hmtx"]
    # Versalhoehe aus dem "H" messen (sCapHeight fehlt in manchen Fonts)
    cap = font["glyf"][cmap[ord("H")]].yMax

    # Glyphen aneinanderreihen (Schriftkoordinaten, y zeigt nach oben)
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


def build(label: str, wheels: int, loeschen: bool, title: str) -> str:
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
  <g fill="#000000">{text_path(label)}</g>
</svg>
"""


# name, Beschriftung, Raeder, Loeschen-Zeichen, Titel
ICONS = [
    # strassengaengig -> 2 Raeder
    ("lf10",      "600",   2, True,  "LF 10/6 - Loeschfahrzeug, 600 l"),
    ("hlf10",     "1000",  2, True,  "HLF 10 - Hilfeleistungsloeschfahrzeug, 1000 l"),
    ("tlf1625",   "2500",  2, True,  "TLF 16/25 - Tankloeschfahrzeug, 2500 l"),
    ("gtlf",      "15000", 2, True,  "GTLF 15000 - Grosstankloeschfahrzeug, 15000 l"),
    ("tsfw750",   "750",   2, True,  "TSF-W - Tragkraftspritzenfahrzeug Wasser, 750 l"),
    ("tsfw500",   "500",   2, True,  "TSF-W - Tragkraftspritzenfahrzeug Wasser, 500 l"),
    ("tsf",       "TSF",   2, True,  "TSF - Tragkraftspritzenfahrzeug"),
    ("klf",       "KLF",   2, True,  "KLF - Kleinloeschfahrzeug"),
    ("elw",       "ELW",   2, False, "ELW - Einsatzleitwagen"),
    ("kdow",      "KdoW",  2, False, "KdoW - Kommandowagen"),
    ("mzf1",      "MZF 1", 2, False, "MZF 1 - Mehrzweckfahrzeug 1"),
    ("mzf2",      "MZF 2", 2, False, "MZF 2 - Mehrzweckfahrzeug 2"),
    # gelaendegaengig -> 3 Raeder
    ("tsfw750gg", "750",   3, True,  "TSF-W 4x4 gelaendegaengig, 750 l"),
    ("tsfw500gg", "500",   3, True,  "TSF-W 4x4 gelaendegaengig, 500 l"),
    ("utv",       "UTV",   3, False, "UTV - Kleinfahrzeug gelaendegaengig"),
]

if __name__ == "__main__":
    for name, label, wheels, loeschen, title in ICONS:
        (OUT / f"{name}.svg").write_text(build(label, wheels, loeschen, title))
        print(f"{name}.svg  [{label}]  {wheels} Raeder{'  +Loeschen' if loeschen else ''}")
