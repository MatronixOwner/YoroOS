#include "bootinfo.h"
#include "cursor.h"
static inline void outb(uint16_t port, uint8_t value) {
    __asm__ volatile("outb %0,%1" : : "a"(value), "Nd"(port));
}
static inline uint8_t inb(uint16_t port) {
    uint8_t value;
    __asm__ volatile("inb %1,%0" : "=a"(value) : "Nd"(port));
    return value;
}
/* An optional marker for automated VM tests. No dependence on serial input. */
static void serial_marker(void) {
    const char *s = "YORO_NATIVE64_RENDERED\n";
    outb(0x3f9, 0); outb(0x3fb, 0x80); outb(0x3f8, 1);
    outb(0x3f9, 0); outb(0x3fb, 3); outb(0x3fa, 0xc7); outb(0x3fc, 3);
    while (*s) {
        unsigned limit = 100000;
        while (limit && !(inb(0x3fd) & 0x20)) --limit;
        if (!limit) break;
        outb(0x3f8, (uint8_t)*s++);
    }
}
void yoro_kernel_main(const struct yoro_framebuffer *fb) {
    static struct yoro_cursor cursor;
    yoro_render(fb);
    yoro_cursor_init(&cursor, fb);
    yoro_cursor_move(&cursor, (int)fb->width / 2, (int)fb->height / 2);
    serial_marker();
    for (;;) __asm__ volatile("hlt");
}
