# Bibata Modern Ice arrow

Source: https://github.com/ful1e5/Bibata_Cursor (author: Abdulkaiz Khatri / ful1e5)
Commit: ddb09273cde49faeb6a32282660ff4293f52d6e0
File: svg/modern/left_ptr.svg; license: GNU GPL version 3 (see LICENSE).

The included SVG is the unmodified source; it uses green/blue placeholder
colors. `tools/generate_bibata_cursor.py` replaces them with the upstream Ice
palette (white fill, black outline), rasterizes at 32x32 with resvg-py and Pillow, and
writes `native64/bibata_cursor_data.h`. The upstream 256x256 hotspot is (55,17),
which rounds to (7,2) at 32x32. The asset and the generated derivative remain
under GPL-3.0; their source and license accompany any distribution.
