/* Simple software desktop mockup: draws only, no input or filesystem. */
#include "bootinfo.h"
#include <stddef.h>

static uint32_t channel(uint8_t value, uint32_t mask) {
    unsigned bits = 0; for (unsigned i = 0; i < 32; ++i) if (mask & (1u << i)) ++bits;
    if (!bits) return 0;
    uint64_t max = (1ULL << bits) - 1;
    uint64_t scaled = ((uint64_t)value * max + 127) / 255;
    uint32_t result = 0; unsigned n = 0;
    for (unsigned i = 0; i < 32; ++i) if (mask & (1u << i)) { if (scaled & (1ULL << n)) result |= 1u << i; ++n; }
    return result;
}
static uint32_t color(const struct yoro_framebuffer *f, int r, int g, int b) {
    return channel((uint8_t)r, f->red_mask) | channel((uint8_t)g, f->green_mask) | channel((uint8_t)b, f->blue_mask);
}
static void rect(const struct yoro_framebuffer *f, int x, int y, int w, int h, uint32_t c) {
    int x0 = x < 0 ? 0 : x, y0 = y < 0 ? 0 : y;
    int x1 = x + w > (int)f->width ? (int)f->width : x + w;
    int y1 = y + h > (int)f->height ? (int)f->height : y + h;
    if (w <= 0 || h <= 0 || x0 >= x1 || y0 >= y1) return;
    for (int j = y0; j < y1; ++j) for (int i = x0; i < x1; ++i)
        f->base[(size_t)j * f->stride + (size_t)i] = c;
}
static void rounded(const struct yoro_framebuffer *f, int x, int y, int w, int h, int r, uint32_t c) {
    if (w <= 0 || h <= 0) return;
    if (r > w / 2) r = w / 2;
    if (r > h / 2) r = h / 2;
    rect(f,x+r,y,w-2*r,h,c); rect(f,x,y+r,r,h-2*r,c); rect(f,x+w-r,y+r,r,h-2*r,c);
    for (int dy=0; dy<r; ++dy) for (int dx=0; dx<r; ++dx)
        if ((r-dx)*(r-dx)+(r-dy)*(r-dy) <= r*r) {
            rect(f,x+dx,y+dy,1,1,c); rect(f,x+w-1-dx,y+dy,1,1,c);
            rect(f,x+dx,y+h-1-dy,1,1,c); rect(f,x+w-1-dx,y+h-1-dy,1,1,c);
        }
}
/* 5x7 uppercase bitmap glyphs, locally authored for the prototype. */
static const uint8_t letters[26][7] = {
 {14,17,17,31,17,17,17},{30,17,17,30,17,17,30},{14,17,16,16,16,17,14},
 {30,17,17,17,17,17,30},{31,16,16,30,16,16,31},{31,16,16,30,16,16,16},
 {14,17,16,23,17,17,15},{17,17,17,31,17,17,17},{31,4,4,4,4,4,31},
 {7,2,2,2,18,18,12},{17,18,20,24,20,18,17},{16,16,16,16,16,16,31},
 {17,27,21,21,17,17,17},{17,25,21,19,17,17,17},{14,17,17,17,17,17,14},
 {30,17,17,30,16,16,16},{14,17,17,17,21,18,13},{30,17,17,30,20,18,17},
 {15,16,16,14,1,1,30},{31,4,4,4,4,4,4},{17,17,17,17,17,17,14},
 {17,17,17,17,17,10,4},{17,17,17,21,21,21,10},{17,17,10,4,10,17,17},
 {17,17,10,4,4,4,4},{31,1,2,4,8,16,31}
};
static void text(const struct yoro_framebuffer *f, int x, int y, int scale, uint32_t c, const char *s) {
    for (; *s; ++s, x += 6*scale) if (*s >= 'A' && *s <= 'Z') {
        const uint8_t *glyph = letters[*s - 'A'];
        for (int row=0; row<7; ++row) for (int col=0; col<5; ++col)
            if (glyph[row] & (1u << (4-col))) rect(f,x+col*scale,y+row*scale,scale,scale,c);
    }
}
static void icon(const struct yoro_framebuffer *f, int x, int y, int type) {
    uint32_t cyan=color(f,91,212,232), blue=color(f,102,133,242), white=color(f,225,238,255);
    rounded(f,x,y,54,54,14,color(f,40,59,96));
    if (type==0) { /* folder */
        rounded(f,x+9,y+17,37,25,4,cyan); rect(f,x+12,y+13,16,6,blue);
        rect(f,x+9,y+23,37,3,white);
    } else if (type==1) { /* document */
        rounded(f,x+14,y+9,26,36,3,white);
        rect(f,x+19,y+18,16,2,blue); rect(f,x+19,y+24,16,2,blue); rect(f,x+19,y+30,10,2,blue);
    } else { /* gear-like settings tile */
        rounded(f,x+12,y+12,30,30,10,blue); rounded(f,x+20,y+20,14,14,5,white);
    }
}
void yoro_render(const struct yoro_framebuffer *f) {
    if (!f || !f->base || !f->width || !f->height || f->width > 8192 || f->height > 8192 ||
        f->stride < f->width || (uint64_t)f->stride * f->height > f->size / 4) return;
    int w=(int)f->width, h=(int)f->height;
    for (int y=0; y<h; ++y) {
        int p=255*y/h;
        rect(f,0,y,w,1,color(f, 13+16*p/255, 24+18*p/255, 53+42*p/255));
    }
    int panel_h = h >= 400 ? 52 : 32;
    rect(f,0,h-panel_h,w,panel_h,color(f,15,23,43));
    rect(f,0,h-panel_h,w,1,color(f,86,114,157));
    text(f,18,h-panel_h+17,2,color(f,160,222,240),"YOROOS");
    if (w >= 480 && h >= 320) {
        int x = w/2 - 190, y = h/2 - 100;
        rounded(f,x,y,380,178,16,color(f,27,39,67));
        rect(f,x+22,y+25,4,42,color(f,83,209,218));
        text(f,x+38,y+26,3,color(f,237,245,255),"YOROOS");
        text(f,x+38,y+60,1,color(f,142,181,214),"NATIVE KERNEL PREVIEW");
        rect(f,x+22,y+87,336,1,color(f,62,80,113));
        text(f,x+24,y+104,2,color(f,198,216,238),"GRAPHICS ONLINE");
        text(f,x+24,y+137,1,color(f,137,168,204),"INPUT AND WINDOWS NOT READY");
        if (w >= 650 && h >= 420) {
            icon(f,30,28,0); text(f,30,89,1,color(f,228,239,255),"FILES");
            icon(f,30,114,1); text(f,30,175,1,color(f,228,239,255),"NOTES");
            icon(f,30,200,2); text(f,30,261,1,color(f,228,239,255),"SETTINGS");
        }
    } else text(f,8,8,1,color(f,237,245,255),"YOROOS NATIVE PREVIEW");
}
