#pragma once
#include "bootinfo.h"
/* One software cursor. Coordinates identify the cursor hotspot, not the
 * sprite's top left. Hide before modifying the underlying framebuffer. */
struct yoro_cursor {
    const struct yoro_framebuffer *fb;
    uint32_t saved[32 * 32];
    int left, top, visible;
};
void yoro_cursor_init(struct yoro_cursor *, const struct yoro_framebuffer *);
void yoro_cursor_move(struct yoro_cursor *, int x, int y);
void yoro_cursor_hide(struct yoro_cursor *);
