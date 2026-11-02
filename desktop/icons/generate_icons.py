#!/usr/bin/env python3
"""Generate the YoroOS SVG app icon set (consistent flat style).

Note: matronix-browser.svg is NOT generated here - it is the real
upstream logo copied from MatronixOwner/Matronix_Browser (assets/logo.svg).

Every icon: 64x64, rounded-square tile with a two-stop diagonal
gradient and a simple white glyph. Run: python3 generate_icons.py
Output: *.svg next to this script.
"""

import os

HERE = os.path.dirname(os.path.abspath(__file__))

TILE = (
    '<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
    '<stop offset="0" stop-color="{c1}"/><stop offset="1" stop-color="{c2}"/>'
    '</linearGradient></defs>'
    '<rect x="3" y="3" width="58" height="58" rx="15" fill="url(#g)"/>'
)

GLYPHS = {
    "yoro-logo": ("#3daee9", "#9b59d0",
        '<path d="M20 16 L32 32 L44 16" fill="none" stroke="#fff" '
        'stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>'
        '<path d="M32 32 L32 49" stroke="#fff" stroke-width="6" '
        'stroke-linecap="round"/>'),
    "yoro-notepad": ("#f5a623", "#e67e22",
        '<path d="M20 12 h16 l8 9 v31 H20 Z" fill="#fff"/>'
        '<path d="M36 12 v9 h8 Z" fill="#ffd9a0"/>'
        '<g stroke="#e67e22" stroke-width="3" stroke-linecap="round">'
        '<path d="M26 29 h12"/><path d="M26 37 h12"/><path d="M26 45 h7"/>'
        '</g>'),
    "yoro-files": ("#2fa8e0", "#1c6dd9",
        '<path d="M12 22 a4 4 0 0 1 4-4 h10 l4 5 h18 a4 4 0 0 1 4 4 '
        'v19 a4 4 0 0 1-4 4 H16 a4 4 0 0 1-4-4 Z" fill="#fff"/>'
        '<path d="M12 31 h40" stroke="#bcd9ff" stroke-width="3"/>'),
    "yoro-media": ("#e93d82", "#9b2c6f",
        '<circle cx="32" cy="32" r="17" fill="none" stroke="#fff" '
        'stroke-width="4"/>'
        '<path d="M27 23 L43 32 L27 41 Z" fill="#fff"/>'),
    "yoro-settings": ("#5b6b7f", "#39424f",
        '<g fill="#fff">'
        + "".join(
            f'<rect x="29" y="10" width="6" height="11" rx="2" '
            f'transform="rotate({a} 32 32)"/>' for a in range(0, 360, 45))
        + '<circle cx="32" cy="32" r="12"/></g>'
        '<circle cx="32" cy="32" r="6" fill="#46505e"/>'),
    "yoro-console": ("#2b2f38", "#14161c",
        '<rect x="12" y="15" width="40" height="34" rx="5" fill="#fff"/>'
        '<path d="M12 24 h40" stroke="#d5d9e0" stroke-width="3"/>'
        '<path d="M19 31 l7 5 -7 5" fill="none" stroke="#14161c" '
        'stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"/>'
        '<path d="M29 42 h8" stroke="#14161c" stroke-width="3.5" '
        'stroke-linecap="round"/>'),
    "yoro-computer": ("#26b6a2", "#147d8a",
        '<rect x="11" y="15" width="42" height="27" rx="4" fill="#fff"/>'
        '<rect x="15" y="19" width="34" height="19" rx="2" fill="#1a8a94"/>'
        '<path d="M32 42 v5 M23 50 h18" stroke="#fff" stroke-width="4" '
        'stroke-linecap="round"/>'),
    "yoro-trash": ("#e05252", "#a83232",
        '<path d="M20 20 h24 l-2.5 27 a4 4 0 0 1-4 3.6 h-11 a4 4 0 0 1-4-3.6 Z" '
        'fill="#fff"/>'
        '<rect x="16" y="15" width="32" height="4.5" rx="2.2" fill="#fff"/>'
        '<rect x="26.5" y="11" width="11" height="4" rx="2" fill="#fff"/>'
        '<g stroke="#c04545" stroke-width="3" stroke-linecap="round">'
        '<path d="M27 27 v15"/><path d="M32 27 v15"/><path d="M37 27 v15"/>'
        '</g>'),
    "yoro-calculator": ("#3f8f5f", "#1f6645",
        '<rect x="17" y="11" width="30" height="42" rx="6" fill="#fff"/>'
        '<rect x="22" y="16.5" width="20" height="8" rx="2" fill="#1f6645"/>'
        '<g fill="#3f8f5f">'
        + "".join(f'<circle cx="{x}" cy="{y}" r="2.6"/>'
                  for y in (31, 38.5, 46) for x in (24.5, 32, 39.5))
        + '</g>'),
    "yoro-paint": ("#f2f2f2", "#cfd4dc",
        '<path d="M32 12 a20 20 0 1 0 8 38.5 c1.8.3 3-1.4 2.7-3.2 '
        'l-.4-2.8 c-.3-2 1.2-3.7 3.2-3.7 h3.6 A8.9 8.9 0 0 0 58 32 '
        'A20 20 0 0 0 32 12Z" fill="#46505e" transform="scale(0.86) '
        'translate(5.2 5.2)"/>'
        '<g><circle cx="24" cy="25" r="3.4" fill="#e05252"/>'
        '<circle cx="36" cy="21" r="3.4" fill="#f5a623"/>'
        '<circle cx="21" cy="37" r="3.4" fill="#2fa8e0"/>'
        '<circle cx="29" cy="45" r="3.4" fill="#2ecc71"/></g>'),
}


def main():
    for name, (c1, c2, glyph) in GLYPHS.items():
        svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
               + TILE.format(c1=c1, c2=c2) + glyph + "</svg>\n")
        path = os.path.join(HERE, f"{name}.svg")
        with open(path, "w", encoding="utf-8") as f:
            f.write(svg)
        print("wrote", path)


if __name__ == "__main__":
    main()
