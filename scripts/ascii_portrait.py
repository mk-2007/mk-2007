"""
Colorized ASCII portrait generator.

Unlike the classic single-color (green/amber) terminal ASCII art look,
this keeps a tint of the subject's real photo colors per character,
blended with an accent color, so it reads as a "glitch/neon portrait"
rather than a plain terminal print.

Usage:
    python3 ascii_portrait.py <input_photo> <output_svg>
"""

import sys
from PIL import Image, ImageOps, ImageEnhance

# Density ramp: index 0 = darkest, last = brightest
CHARS = " .:-=+*#%@"

# Brand accent used elsewhere in the profile (buttons, headers)
ACCENT = (167, 139, 250)  # #A78BFA
BG = "#0d1117"

FONT_SIZE = 9.2
CHAR_W = FONT_SIZE * 0.6   # monospace advance width approximation
LINE_H = FONT_SIZE * 1.0


def load_and_crop(path, target_ratio=0.82, zoom=1.55, vertical_bias=0.32):
    im = Image.open(path).convert("RGB")
    im = ImageOps.exif_transpose(im)
    w, h = im.size

    # Zoom in around the subject first: crop out the outer margins so the
    # face/shoulders fill the frame instead of a wide selfie background.
    zw, zh = w / zoom, h / zoom
    left = (w - zw) * 0.5
    top = (h - zh) * vertical_bias
    im = im.crop((int(left), int(top), int(left + zw), int(top + zh)))
    w, h = im.size

    # Then crop to a clean portrait ratio, centered.
    cur_ratio = w / h
    if cur_ratio > target_ratio:
        new_w = int(h * target_ratio)
        left = (w - new_w) // 2
        im = im.crop((left, 0, left + new_w, h))
    else:
        new_h = int(w / target_ratio)
        top = int((h - new_h) * 0.1)
        im = im.crop((0, top, w, top + new_h))

    im = ImageEnhance.Contrast(im).enhance(1.15)
    im = ImageEnhance.Color(im).enhance(1.2)
    return im


def blend(rgb, accent, amount):
    return tuple(int(rgb[i] * (1 - amount) + accent[i] * amount) for i in range(3))


def build_grid(im, cols):
    w, h = im.size
    cell_w = w / cols
    cell_h = cell_w / 0.5  # characters are ~2x taller than wide
    rows = max(1, int(h / cell_h))
    small = im.resize((cols, rows), Image.LANCZOS)
    return small, cols, rows


def to_svg(im, cols, out_path):
    small, cols, rows = build_grid(im, cols)
    pixels = small.load()

    width = cols * CHAR_W
    height = rows * LINE_H
    pad = 26

    svg_w = width + pad * 2
    svg_h = height + pad * 2 + 34  # extra bottom strip for caption

    parts = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{svg_w:.0f}" '
        f'height="{svg_h:.0f}" viewBox="0 0 {svg_w:.0f} {svg_h:.0f}">'
    )

    # Defs: background gradient + glow filter + border gradient
    parts.append('<defs>')
    parts.append(
        '<linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">'
        '<stop offset="0%" stop-color="#0d1117"/>'
        '<stop offset="100%" stop-color="#161022"/>'
        '</linearGradient>'
    )
    parts.append(
        '<linearGradient id="borderGrad" x1="0%" y1="0%" x2="100%" y2="100%">'
        '<stop offset="0%" stop-color="#A78BFA"/>'
        '<stop offset="50%" stop-color="#6D5BD0"/>'
        '<stop offset="100%" stop-color="#A78BFA"/>'
        '</linearGradient>'
    )
    parts.append(
        '<filter id="glow" x="-20%" y="-20%" width="140%" height="140%">'
        '<feGaussianBlur stdDeviation="1.1" result="blur"/>'
        '<feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>'
        '</filter>'
    )
    parts.append('</defs>')

    # Background + border frame
    parts.append(f'<rect width="{svg_w:.0f}" height="{svg_h:.0f}" rx="14" fill="url(#bgGrad)"/>')
    parts.append(
        f'<rect x="4" y="4" width="{svg_w - 8:.0f}" height="{svg_h - 8:.0f}" rx="12" '
        f'fill="none" stroke="url(#borderGrad)" stroke-width="1.6" opacity="0.85"/>'
    )

    parts.append(
        f'<g font-family="Fira Code, Consolas, monospace" font-size="{FONT_SIZE}" '
        f'filter="url(#glow)">'
    )

    n_chars = len(CHARS) - 1
    for row in range(rows):
        y = pad + (row + 1) * LINE_H - LINE_H * 0.25
        tspans = []
        for col in range(cols):
            r, g, b = pixels[col, row]
            lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255.0
            idx = min(n_chars, int(lum * n_chars))
            ch = CHARS[idx]
            if ch == " ":
                continue
            # Blend the real pixel color with the accent, more accent in shadows
            amt = 0.35 - (lum * 0.25)
            amt = max(0.08, min(0.4, amt))
            cr, cg, cb = blend((r, g, b), ACCENT, amt)
            opacity = 0.35 + lum * 0.65
            x = pad + col * CHAR_W
            tspans.append(
                f'<text x="{x:.1f}" y="{y:.1f}" fill="rgb({cr},{cg},{cb})" '
                f'fill-opacity="{opacity:.2f}">{ch}</text>'
            )
        parts.extend(tspans)

    parts.append('</g>')

    # Caption strip
    cap_y = svg_h - 14
    parts.append(
        f'<text x="{pad}" y="{cap_y:.0f}" font-family="Fira Code, monospace" '
        f'font-size="11" fill="#A78BFA" opacity="0.85">'
        f'&gt; rendered from selfie.jpg — {cols}x{rows} glyphs</text>'
    )

    parts.append('</svg>')

    with open(out_path, "w") as f:
        f.write("".join(parts))


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "source-photo.jpg"
    out = sys.argv[2] if len(sys.argv) > 2 else "ascii-portrait.svg"
    cols = int(sys.argv[3]) if len(sys.argv) > 3 else 78
    img = load_and_crop(src)
    to_svg(img, cols, out)
    print(f"Wrote {out}")
