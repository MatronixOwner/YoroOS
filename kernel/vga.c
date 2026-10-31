#include "vga.h"
#include "io.h"
#include "string.h"

#include <stdarg.h>

#define VGA_MEMORY ((volatile uint16_t *)0xB8000)
#define VGA_WIDTH 80
#define VGA_HEIGHT 25

static size_t cursor_x = 0;
static size_t cursor_y = 0;
static uint8_t color = 0x07; /* фоновый|текст: светлосерый на чёрном */

static void update_cursor(void) {
    uint16_t pos = (uint16_t)(cursor_y * VGA_WIDTH + cursor_x);
    outb(0x3D4, 0x0F);
    outb(0x3D5, (uint8_t)(pos & 0xFF));
    outb(0x3D4, 0x0E);
    outb(0x3D5, (uint8_t)((pos >> 8) & 0xFF));
}

static void scroll(void) {
    volatile uint16_t *mem = VGA_MEMORY;
    for (size_t y = 1; y < VGA_HEIGHT; y++)
        for (size_t x = 0; x < VGA_WIDTH; x++)
            mem[(y - 1) * VGA_WIDTH + x] = mem[y * VGA_WIDTH + x];
    uint16_t blank = (uint16_t)((uint16_t)color << 8) | ' ';
    for (size_t x = 0; x < VGA_WIDTH; x++)
        mem[(VGA_HEIGHT - 1) * VGA_WIDTH + x] = blank;
    cursor_y = VGA_HEIGHT - 1;
}

void vga_init(void) {
    color = VGA_LIGHT_GREY | (VGA_BLACK << 4);
    vga_clear();
}

void vga_clear(void) {
    volatile uint16_t *mem = VGA_MEMORY;
    uint16_t blank = (uint16_t)((uint16_t)color << 8) | ' ';
    for (size_t i = 0; i < VGA_WIDTH * VGA_HEIGHT; i++)
        mem[i] = blank;
    cursor_x = 0;
    cursor_y = 0;
    update_cursor();
}

void vga_setcolor(uint8_t fg, uint8_t bg) {
    color = (uint8_t)(fg | (bg << 4));
}

uint8_t vga_get_fg(void) {
    return (uint8_t)(color & 0x0F);
}

void vga_putchar(char c) {
    volatile uint16_t *mem = VGA_MEMORY;

    if (c == '\n') {
        cursor_x = 0;
        cursor_y++;
    } else if (c == '\r') {
        cursor_x = 0;
    } else if (c == '\b') {
        if (cursor_x > 0) {
            cursor_x--;
            mem[cursor_y * VGA_WIDTH + cursor_x] =
                (uint16_t)((uint16_t)color << 8) | ' ';
        }
    } else if (c == '\t') {
        size_t next = (cursor_x + 4) & ~(size_t)3;
        while (cursor_x < next)
            vga_putchar(' ');
        return;
    } else {
        mem[cursor_y * VGA_WIDTH + cursor_x] =
            (uint16_t)((uint16_t)color << 8) | (uint8_t)c;
        cursor_x++;
        if (cursor_x >= VGA_WIDTH) {
            cursor_x = 0;
            cursor_y++;
        }
    }

    if (cursor_y >= VGA_HEIGHT)
        scroll();
    update_cursor();
}

void vga_puts(const char *s) {
    while (*s)
        vga_putchar(*s++);
}

void vga_printf(const char *fmt, ...) {
    va_list ap;
    va_start(ap, fmt);
    char numbuf[32];

    for (const char *p = fmt; *p; p++) {
        if (*p != '%') {
            vga_putchar(*p);
            continue;
        }
        p++; /* то */

        /* %02d / %04d style zero padding (single digit width). */
        int zero_pad = 0;
        if (*p == '0' && p[1] >= '0' && p[1] <= '9') {
            zero_pad = p[1] - '0';
            p += 2;
        }

        switch (*p) {
        case 's': {
            const char *s = va_arg(ap, const char *);
            vga_puts(s ? s : "(null)");
            break;
        }
        case 'c':
            vga_putchar((char)va_arg(ap, int));
            break;
        case 'd':
        case 'i': {
            itoa(va_arg(ap, int), numbuf);
            if (zero_pad) {
                size_t len = strlen(numbuf);
                while ((int)len < zero_pad) {
                    vga_putchar('0');
                    len++;
                }
            }
            vga_puts(numbuf);
            break;
        }
        case 'u':
            utoa(va_arg(ap, uint32_t), numbuf, 10);
            vga_puts(numbuf);
            break;
        case 'x':
        case 'X':
            utoa(va_arg(ap, uint32_t), numbuf, 16);
            vga_puts(numbuf);
            break;
        case '%':
            vga_putchar('%');
            break;
        default:
            vga_putchar('%');
            if (*p)
                vga_putchar(*p);
            break;
        }
    }

    va_end(ap);
}
