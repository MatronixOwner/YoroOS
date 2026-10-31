#include "keyboard.h"
#include "io.h"
#include "types.h"

/* Scancode set 1 -> ASCII (US layout). Index = make code. */
static const char keymap[128] = {
    0,    27,   '1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '-', '=', '\b',
    '\t', 'q',  'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p', '[', ']', '\n',
    0, /* LCtrl */
    'a',  's',  'd', 'f', 'g', 'h', 'j', 'k', 'l', ';', '\'', '`',
    0, /* LShift */
    '\\', 'z',  'x', 'c', 'v', 'b', 'n', 'm', ',', '.', '/',
    0, /* RShift */
    '*',
    0, /* LAlt */
    ' ',
    0, /* CapsLock */
    /* F1-F10, NumLock, ScrollLock, keypad: unmapped */
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    '7', '8', '9', '-', '4', '5', '6', '+', '1', '2', '3', '0', '.',
};

static const char keymap_shift[128] = {
    0,    27,   '!', '@', '#', '$', '%', '^', '&', '*', '(', ')', '_', '+', '\b',
    '\t', 'Q',  'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P', '{', '}', '\n',
    0,
    'A',  'S',  'D', 'F', 'G', 'H', 'J', 'K', 'L', ':', '"', '~',
    0,
    '|',  'Z',  'X', 'C', 'V', 'B', 'N', 'M', '<', '>', '?',
    0,
    '*',
    0,
    ' ',
    0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    '7', '8', '9', '-', '4', '5', '6', '+', '1', '2', '3', '0', '.',
};

static bool shift_pressed = false;
static bool ctrl_pressed = false;
static bool caps_lock = false;

static uint8_t read_scancode(void) {
    while ((inb(0x64) & 0x01) == 0)
        ;
    return inb(0x60);
}

int keyboard_readkey(void) {
    for (;;) {
        uint8_t code = read_scancode();

        /* Extended keys (arrows etc.), prefix 0xE0. */
        if (code == 0xE0) {
            uint8_t ext = read_scancode();
            switch (ext) {
            case 0x48: return KEY_UP;
            case 0x50: return KEY_DOWN;
            case 0x4B: return KEY_LEFT;
            case 0x4D: return KEY_RIGHT;
            case 0x1C: return '\n'; /* keypad Enter */
            case 0x35: return '/';  /* keypad / */
            case 0x1D: ctrl_pressed = true; break;  /* RCtrl make */
            case 0x9D: ctrl_pressed = false; break; /* RCtrl break */
            default: break;
            }
            continue;
        }

        bool released = (code & 0x80) != 0;
        uint8_t make = (uint8_t)(code & 0x7F);

        if (make == 0x2A || make == 0x36) { /* LShift / RShift */
            shift_pressed = !released;
            continue;
        }
        if (make == 0x1D) { /* LCtrl */
            ctrl_pressed = !released;
            continue;
        }
        if (make == 0x3A) { /* CapsLock */
            if (!released)
                caps_lock = !caps_lock;
            continue;
        }
        if (released)
            continue;

        if (make >= 128)
            continue;

        char c = keymap[make];
        if (c == 0)
            continue;

        bool is_letter = (c >= 'a' && c <= 'z');
        bool upper = is_letter ? (shift_pressed ^ caps_lock) : shift_pressed;
        if (upper)
            c = keymap_shift[make];

        if (ctrl_pressed && is_letter)
            return (keymap[make] - 'a' + 1); /* Ctrl+A=1 .. Ctrl+Z=26 */

        return c;
    }
}
