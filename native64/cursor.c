#include "cursor.h"
#include "bibata_cursor_data.h"
#include <stddef.h>

/* Masks may be non-contiguous in GOP's PixelBitMask format. */
static unsigned extract(uint32_t pixel, uint32_t mask) {
    uint64_t raw = 0; unsigned count = 0;
    for (unsigned i=0; i<32; ++i) if (mask & (1u<<i)) {
        if (pixel & (1u<<i)) raw |= 1ULL<<count;
        ++count;
    }
    if (!count) return 0;
    uint64_t max = (1ULL << count) - 1;
    return (unsigned)((raw * 255 + max/2) / max);
}
static uint32_t pack(unsigned value, uint32_t mask) {
    unsigned count = 0; for (unsigned i=0; i<32; ++i) if (mask & (1u<<i)) ++count;
    if (!count) return 0;
    uint64_t max = (1ULL << count) - 1, raw = (value * max + 127) / 255;
    uint32_t out=0; unsigned n=0;
    for (unsigned i=0; i<32; ++i) if (mask & (1u<<i)) {
        if (raw & (1ULL<<n)) out |= 1u<<i;
        ++n;
    }
    return out;
}
static int valid(const struct yoro_framebuffer *f) {
    return f && f->base && f->width && f->height && f->width <= 8192 && f->height <= 8192 &&
           f->stride >= f->width && (uint64_t)f->stride * f->height <= f->size / 4;
}
void yoro_cursor_init(struct yoro_cursor *c, const struct yoro_framebuffer *fb) {
    c->fb=fb; c->left=0; c->top=0; c->visible=0;
}
void yoro_cursor_hide(struct yoro_cursor *c) {
    const struct yoro_framebuffer *f = c->fb;
    if (!c->visible || !valid(f)) return;
    for (int y=0; y<32; ++y) for (int x=0; x<32; ++x) {
        int px=c->left+x, py=c->top+y;
        if (px>=0 && py>=0 && px<(int)f->width && py<(int)f->height)
            f->base[(size_t)py*f->stride+(size_t)px] = c->saved[y*32+x];
    }
    c->visible=0;
}
void yoro_cursor_move(struct yoro_cursor *c, int x, int y) {
    const struct yoro_framebuffer *f = c->fb;
    if (!valid(f)) return;
    yoro_cursor_hide(c);
    if (x<0) x=0;
    if (x>=(int)f->width) x=(int)f->width-1;
    if (y<0) y=0;
    if (y>=(int)f->height) y=(int)f->height-1;
    c->left=x-7; c->top=y-2; /* Upstream hotspot 55,17 on 256px source. */
    for (int sy=0; sy<32; ++sy) for (int sx=0; sx<32; ++sx) {
        int px=c->left+sx, py=c->top+sy;
        if (px<0 || py<0 || px>=(int)f->width || py>=(int)f->height) continue;
        size_t pos=(size_t)py*f->stride+(size_t)px;
        uint32_t background=f->base[pos];
        c->saved[sy*32+sx]=background;
        uint32_t src=yoro_bibata_rgba[sy*32+sx];
        unsigned a=src>>24; if (!a) continue;
        unsigned r=((src>>16)&255)*a+extract(background,f->red_mask)*(255-a);
        unsigned g=((src>>8)&255)*a+extract(background,f->green_mask)*(255-a);
        unsigned b=(src&255)*a+extract(background,f->blue_mask)*(255-a);
        uint32_t rgb=pack((r+127)/255,f->red_mask) | pack((g+127)/255,f->green_mask) | pack((b+127)/255,f->blue_mask);
        f->base[pos]=(background & ~(f->red_mask|f->green_mask|f->blue_mask)) | rgb;
    }
    c->visible=1;
}
