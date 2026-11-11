#!/usr/bin/env python3
"""Generate our 32px GPL-3.0 Bibata sprite from the upstream SVG source.
Requires resvg-py==0.5.0 and Pillow for offline asset regeneration.
"""
import pathlib
import io
import resvg_py
from PIL import Image

root = pathlib.Path(__file__).resolve().parents[1]
svg = (root / 'assets/cursors/bibata/left_ptr.svg').read_text()
svg = svg.replace('#00FF00', '#FFFFFF').replace('#0000FF', '#000000')
png = resvg_py.svg_to_bytes(svg_string=svg, width=32, height=32)
pixels = Image.open(io.BytesIO(png)).convert('RGBA').tobytes()
assert len(pixels) == 32 * 32 * 4
out = ['/* Generated from Bibata Modern Ice. GPL-3.0; see assets/cursors/bibata. */',
       '#pragma once', '#include <stdint.h>',
       'static const uint32_t yoro_bibata_rgba[1024] = {']
for n in range(0, len(pixels), 4 * 8):
    line = []
    for i in range(n, n + 4 * 8, 4):
        r, g, b, a = pixels[i:i+4]
        line.append('0x%02x%02x%02x%02xu' % (a, r, g, b))
    out.append('    ' + ', '.join(line) + ',')
out += ['};', '']
(root / 'native64/bibata_cursor_data.h').write_text('\n'.join(out))
