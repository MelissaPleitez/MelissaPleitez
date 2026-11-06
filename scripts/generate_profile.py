#!/usr/bin/env python3
"""
MELISSA PLEITEZ — Profile assets generator

Only the name uses the handwritten Excalifont (converted to vector paths).
Everything else uses system fonts so GitHub renders it consistently.

Run:
    python scripts/generate_profile.py

Dependencies:
    pip install fonttools brotli

Output:
    assets/banner-dark.svg
    assets/banner-light.svg
    assets/technical-landscape-dark.svg
    assets/technical-landscape-light.svg

Animations are SMIL (they play inside <img> on GitHub):
  - the name is revealed as if it were being written
  - the underline draws itself
  - data packets travel through the systems map
  - two faint orbits rotate slowly around the backend
  - a request travels down the technical stack
"""

import math
from pathlib import Path
from urllib.request import urlopen
from html import escape
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
FONT_DIR = ASSETS / "fonts"
FONT_FILE = FONT_DIR / "Excalifont.woff2"

FONT_URL = (
    "https://raw.githubusercontent.com/excalidraw/excalidraw/"
    "master/packages/excalidraw/fonts/Excalifont/"
    "Excalifont-Regular-a88b72a24fb54c9f94e3b5fdaa7481c9.woff2"
)

SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"
MONO = "ui-monospace,SFMono-Regular,Consolas,monospace"

THEMES = {
    "dark": {
        "bg": "#151515",
        "surface": "#202020",
        "surface2": "#292929",
        "text": "#F5F0E7",
        "muted": "#A49D91",
        "line": "#45413B",
        "orange": "#FF642D",
        "orange_soft": "#39251E",
        "grid": "#FFFFFF",
        "glow": "0.20",
    },
    "light": {
        "bg": "#F4F0E7",
        "surface": "#FFFDF7",
        "surface2": "#EAE4D8",
        "text": "#171717",
        "muted": "#6B655C",
        "line": "#D2C9BA",
        "orange": "#E95420",
        "orange_soft": "#FBE0D3",
        "grid": "#28231D",
        "glow": "0.15",
    },
}


# ---------------------------------------------------------
# FONT: Excalifont glyphs -> SVG paths (used for the name only)
# ---------------------------------------------------------

def load_font():
    FONT_DIR.mkdir(parents=True, exist_ok=True)

    if not FONT_FILE.exists():
        print("Downloading Excalifont...")
        with urlopen(FONT_URL, timeout=30) as response:
            FONT_FILE.write_bytes(response.read())

    font = TTFont(FONT_FILE)
    return {
        "glyphs": font.getGlyphSet(),
        "cmap": font.getBestCmap(),
        "metrics": font["hmtx"].metrics,
        "units": font["head"].unitsPerEm,
    }


def hand_text(font, x, baseline, value, size, color, letter_spacing=0):
    scale = size / font["units"]
    cursor = x
    paths = []

    for character in value:
        if character == " ":
            cursor += font["units"] * scale * 0.32
            continue

        glyph_name = font["cmap"].get(ord(character), ".notdef")
        pen = SVGPathPen(font["glyphs"])
        font["glyphs"][glyph_name].draw(pen)
        path_data = pen.getCommands()

        if path_data:
            paths.append(
                f'<path d="{path_data}" fill="{color}" '
                f'transform="translate({cursor:.2f},{baseline:.2f}) '
                f'scale({scale:.6f},-{scale:.6f})"/>'
            )

        cursor += font["metrics"][glyph_name][0] * scale + letter_spacing

    return "".join(paths)


# ---------------------------------------------------------
# SVG HELPERS
# ---------------------------------------------------------

def rect(x, y, w, h, fill, radius=0, stroke="none", sw=1):
    return (
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
    )


def txt(x, y, value, size, color, family=SANS, weight=400,
        anchor="start", spacing=0):
    return (
        f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" '
        f'font-weight="{weight}" letter-spacing="{spacing}" '
        f'text-anchor="{anchor}" fill="{color}">{escape(str(value))}</text>'
    )


def circle(x, y, r, fill, stroke="none", sw=1, opacity=1):
    return (
        f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}" '
        f'stroke="{stroke}" stroke-width="{sw}" opacity="{opacity}"/>'
    )


def pulse(x, y, color, r=4):
    """Dot with an expanding ring."""
    return (
        circle(x, y, r, color)
        + f'<circle cx="{x}" cy="{y}" r="{r}" fill="none" '
          f'stroke="{color}" stroke-width="1.5">'
          f'<animate attributeName="r" values="{r};{r * 3}" dur="2s" '
          'repeatCount="indefinite"/>'
          '<animate attributeName="opacity" values=".8;0" dur="2s" '
          'repeatCount="indefinite"/></circle>'
    )


def backdrop(t, width, height):
    """Background, one soft glow and a faint grid."""
    return (
        '<defs>'
        '<pattern id="grid" width="32" height="32" '
        'patternUnits="userSpaceOnUse">'
        f'<path d="M32 0H0V32" fill="none" stroke="{t["grid"]}" '
        'stroke-opacity=".045"/></pattern>'
        f'<radialGradient id="glow" cx="{width * .74}" cy="{height * .5}" '
        f'r="{width * .42}" gradientUnits="userSpaceOnUse">'
        f'<stop offset="0" stop-color="{t["orange"]}" '
        f'stop-opacity="{t["glow"]}"/>'
        f'<stop offset="1" stop-color="{t["orange"]}" stop-opacity="0"/>'
        '</radialGradient></defs>'
        + rect(0, 0, width, height, t["bg"])
        + f'<rect width="{width}" height="{height}" fill="url(#grid)"/>'
        + f'<rect width="{width}" height="{height}" fill="url(#glow)"/>'
    )


# ---------------------------------------------------------
# BANNER: name on the left, living systems map on the right
# ---------------------------------------------------------

CENTER = (890, 310)

# label, x, y, accent, flow direction ("in" = toward backend, "out" = away)
SATELLITES = [
    ("REST APIs", 755, 160, False, "in"),
    ("React",     1035, 150, False, "in"),
    ("Docker",    700, 315, False, "in"),
    ("PostgreSQL", 1060, 320, False, "out"),
    ("Redis",     765, 470, False, "out"),
    ("AI + RAG",  1015, 475, True,  "out"),
]


def curve(x1, y1, x2, y2, bend=0.18):
    """Quadratic curve between two points with a gentle bend."""
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    dx, dy = x2 - x1, y2 - y1
    cx, cy = mx - dy * bend, my + dx * bend
    return f"M{x1} {y1} Q{cx:.1f} {cy:.1f} {x2} {y2}"


def systems_map(t):
    cx, cy = CENTER
    parts = []

    # Rotating orbits (decorative, very quiet).
    for radius, direction, dur, dots in ((118, 1, 46, 2), (205, -1, 70, 3)):
        spin = 360 * direction
        group = [
            f'<g><animateTransform attributeName="transform" type="rotate" '
            f'from="0 {cx} {cy}" to="{spin} {cx} {cy}" dur="{dur}s" '
            'repeatCount="indefinite"/>',
            circle(cx, cy, radius, "none", t["line"], 1, 0.9)
            .replace('stroke-width="1"',
                     'stroke-width="1" stroke-dasharray="2 7"'),
        ]
        for i in range(dots):
            angle = i * 6.2832 / dots + 0.6
            px = cx + radius * math.cos(angle)
            py = cy + radius * math.sin(angle)
            group.append(circle(round(px, 1), round(py, 1), 3, t["orange"],
                                opacity=0.55))
        group.append("</g>")
        parts.append("".join(group))

    # Connections with flowing dashes and travelling packets.
    for i, (label, sx, sy, accent, flow) in enumerate(SATELLITES):
        if flow == "in":
            d = curve(sx, sy, cx, cy)
        else:
            d = curve(cx, cy, sx, sy)

        parts.append(
            f'<path d="{d}" fill="none" stroke="{t["orange"]}" '
            f'stroke-width="{1.8 if accent else 1.3}" '
            f'stroke-opacity="{0.9 if accent else 0.45}" '
            'stroke-dasharray="5 7" stroke-linecap="round">'
            '<animate attributeName="stroke-dashoffset" '
            f'from="{24 if flow == "in" else 0}" '
            f'to="{0 if flow == "in" else 24}" dur="1.6s" '
            'repeatCount="indefinite"/></path>'
        )
        parts.append(
            f'<circle r="{4.5 if accent else 3.5}" fill="{t["orange"]}">'
            f'<animateMotion dur="{3.2 + i * 0.35:.2f}s" '
            f'begin="{i * 0.5:.1f}s" repeatCount="indefinite" '
            f'path="{d}"/></circle>'
        )

    # Backend core.
    parts.append(
        f'<circle cx="{cx}" cy="{cy}" r="62" fill="none" '
        f'stroke="{t["orange"]}" stroke-width="1.5">'
        '<animate attributeName="r" values="62;96" dur="3s" '
        'repeatCount="indefinite"/>'
        '<animate attributeName="opacity" values=".55;0" dur="3s" '
        'repeatCount="indefinite"/></circle>'
    )
    parts.append(circle(cx, cy, 62, t["orange_soft"], t["orange"], 2))
    parts.append(txt(cx, cy - 2, "Backend", 21, t["text"], weight=700,
                     anchor="middle"))
    parts.append(txt(cx, cy + 20, "Node.js · NestJS", 12, t["muted"],
                     anchor="middle"))

    # Satellite pills.
    for label, sx, sy, accent, _ in SATELLITES:
        w = max(82, round(len(label) * 8.4 + 36))
        parts.append(rect(sx - w / 2, sy - 20, w, 40, t["surface"], 20,
                          t["orange"] if accent else t["line"],
                          1.8 if accent else 1.3))
        parts.append(txt(sx, sy + 5, label, 14, t["text"], weight=600,
                         anchor="middle"))

    return "".join(parts)


def render_banner(theme_name, font):
    t = THEMES[theme_name]
    W, H = 1200, 600

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}" role="img" aria-labelledby="title desc">',
        '<title id="title">Melissa Pleitez — Backend-focused Full-Stack Developer</title>',
        '<desc id="desc">Animated profile banner: a systems map connecting '
        'APIs, data, AI and product around a backend core.</desc>',
        backdrop(t, W, H),

        # Wipe that reveals the name as if it were being written.
        '<defs><clipPath id="write"><rect x="40" y="130" width="600" '
        'height="270">'
        '<animate attributeName="width" from="0" to="600" begin="0s" '
        'dur="1.6s" calcMode="spline" keyTimes="0;1" '
        'keySplines=".4 0 .2 1" fill="freeze"/></rect></clipPath></defs>',

        txt(66, 150, "Hi, I'm", 22, t["muted"], weight=500),
        '<g clip-path="url(#write)">'
        + hand_text(font, 55, 262, "Melissa", 124, t["text"])
        + hand_text(font, 63, 352, "Pleitez", 92, t["orange"])
        + '</g>',

        # Underline that draws itself after the name.
        f'<path d="M68 376 Q150 364 230 374 T410 370" fill="none" '
        f'stroke="{t["orange"]}" stroke-width="6" stroke-linecap="round" '
        'stroke-dasharray="380" stroke-dashoffset="380">'
        '<animate attributeName="stroke-dashoffset" from="380" to="0" '
        'begin="1.2s" dur="0.9s" fill="freeze"/></path>',

        txt(66, 436, "Backend-focused Full-Stack Developer", 24, t["text"],
            weight=700),
        txt(66, 470, "I build systems that connect people, data and products.",
            16, t["muted"]),

        # Quiet facts
        circle(72, 512, 3.5, t["orange"]),
        txt(88, 517, "4+ years building software", 15, t["text"], weight=500),
        circle(72, 540, 3.5, t["orange"]),
        txt(88, 545, "Telecom, fintech and logistics", 15, t["text"],
            weight=500),
        circle(72, 568, 3.5, t["orange"]),
        txt(88, 573, "El Salvador, remote across LATAM", 15, t["text"],
            weight=500),

        systems_map(t),
        '</svg>',
    ]
    return "".join(parts)


# ---------------------------------------------------------
# TECHNICAL LANDSCAPE: layered stack with a request travelling down
# ---------------------------------------------------------

LAYERS = [
    ("Product", "Interfaces people actually enjoy using.",
     ["React", "React Native", "JavaScript"], False),
    ("Backend", "APIs and services built for production.",
     ["Node.js", "NestJS", "TypeScript", "PHP", "REST APIs"], False),
    ("AI engineering", "LLM features that are typed and grounded.",
     ["Vercel AI SDK", "Zod", "Structured Outputs", "Tool Calling",
      "Embeddings", "RAG"], True),
    ("Data and infrastructure", "Reliable data, tuned and shipped.",
     ["PostgreSQL", "Redis", "pgvector", "TypeORM", "Docker"], False),
    ("Dev environment", "A fast loop from commit to production.",
     ["Git", "GitHub Actions", "Cursor", "Claude Code"], False),
]


def layer_chips(t, x_start, x_end, row_y, row_h, items, accent):
    """Lay chips out, wrapping to a second line when needed."""
    sizes = [max(64, round(len(n) * 7.3 + 32)) for n in items]
    lines, current, used = [], [], 0
    for name, w in zip(items, sizes):
        if current and x_start + used + w > x_end:
            lines.append(current)
            current, used = [], 0
        current.append((name, w))
        used += w + 8
    lines.append(current)

    chip_h, gap = 32, 6
    block = len(lines) * chip_h + (len(lines) - 1) * gap
    y = row_y + (row_h - block) / 2
    out = []
    for line in lines:
        x = x_start
        for name, w in line:
            out.append(rect(x, y, w, chip_h, t["bg"] if not accent
                            else t["surface"], 16,
                            t["orange"] if accent else t["line"], 1.2))
            out.append(txt(x + w / 2, y + 20.5, name, 12, t["text"],
                           family=MONO, anchor="middle"))
            x += w + 8
        y += chip_h + gap
    return "".join(out)


def render_landscape(theme_name, font):
    t = THEMES[theme_name]
    W, H = 1200, 815
    row_h, gap, top = 100, 14, 190

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}" role="img" aria-labelledby="title desc">',
        '<title id="title">Melissa Pleitez — Technical landscape</title>',
        '<desc id="desc">The stack I work with, from product to '
        'infrastructure.</desc>',
        backdrop(t, W, H),

        txt(60, 100, "My technical world", 44, t["text"], weight=800,
            spacing=-1),
        txt(60, 136, "The layers I work across, from the screen to the "
            "database and the model.", 16, t["muted"]),
    ]

    spine_x = 84
    first_mid = top + row_h / 2
    last_mid = top + (len(LAYERS) - 1) * (row_h + gap) + row_h / 2

    # Spine that connects the layers.
    parts.append(
        f'<path d="M{spine_x} {first_mid} V{last_mid}" stroke="{t["line"]}" '
        'stroke-width="2" fill="none"/>'
    )

    for i, (title, desc, items, accent) in enumerate(LAYERS):
        y = top + i * (row_h + gap)
        mid = y + row_h / 2

        parts.append(rect(120, y, 1020, row_h, t["orange_soft"] if accent
                          else t["surface"], 16,
                          t["orange"] if accent else t["line"],
                          1.8 if accent else 1.2))
        parts.append(circle(spine_x, mid, 7, t["bg"],
                            t["orange"] if accent else t["muted"], 2))
        parts.append(txt(148, y + 44, title, 20, t["text"], weight=700))
        parts.append(txt(148, y + 69, desc, 13.5, t["muted"]))

        if accent:
            parts.append(rect(300, y + 26, 112, 24, t["bg"], 12,
                              t["orange"], 1))
            parts.append(pulse(316, y + 38, t["orange"], 3))
            parts.append(txt(366, y + 42.5, "Current focus", 11.5,
                             t["orange"], weight=700, anchor="middle"))

        parts.append(layer_chips(t, 470, 1116, y, row_h, items, accent))

    # A request travelling down the stack.
    parts.append(
        f'<circle r="5.5" fill="{t["orange"]}">'
        f'<animateMotion dur="5s" repeatCount="indefinite" '
        f'path="M{spine_x} {first_mid} V{last_mid}"/></circle>'
    )

    parts.extend([
        txt(60, 792, "Melissa Pleitez", 13, t["text"], weight=700),
        txt(1140, 792, "Backend, data, AI and product.", 13, t["muted"],
            anchor="end"),
        '</svg>',
    ])
    return "".join(parts)


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

def main():
    ASSETS.mkdir(parents=True, exist_ok=True)

    print("Loading Excalifont and converting glyphs...")
    font = load_font()

    generators = {
        "banner": render_banner,
        "technical-landscape": render_landscape,
    }

    for name, generator in generators.items():
        for theme in ("dark", "light"):
            output = ASSETS / f"{name}-{theme}.svg"
            output.write_text(generator(theme, font), encoding="utf-8")
            print(f"Generated: {output.relative_to(ROOT)}")

    print("\nDone. All SVG files are ready.")


if __name__ == "__main__":
    main()