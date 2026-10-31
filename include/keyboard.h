#pragma once

/* PS/2 keyboard driver (polling, scancode set 1, US layout). */

/* Special (non-ASCII) key codes returned by keyboard_readkey(). */
#define KEY_UP    0x100
#define KEY_DOWN  0x101
#define KEY_LEFT  0x102
#define KEY_RIGHT 0x103

/*
 * Block until a key is pressed.
 * Returns an ASCII code (with '\n', '\b', '\t', Ctrl+letter codes)
 * or one of the KEY_* constants above.
 */
int keyboard_readkey(void);
