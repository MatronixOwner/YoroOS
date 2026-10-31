#!/usr/bin/env python3
"""
End-to-end boot test for a YoroOS ISO using the Unicorn emulator.

This runs the real machine code from the ISO: BIOS boot sector ->
32-bit kernel -> interactive shell. A small fake BIOS (INT 10h/13h/15h),
PS/2 keyboard and CMOS/RTC are emulated in Python; VGA text memory at
0xB8000 is captured and printed as the "screen".

Requires: pip install unicorn

Usage: emutest.py <image.iso>
Exit code 0 = all checks passed.
"""

import struct
import sys

from unicorn import Uc, UcError, UC_ARCH_X86, UC_MODE_16, UC_HOOK_CODE
from unicorn.x86_const import (
    UC_X86_REG_EAX,
    UC_X86_REG_EBX,
    UC_X86_REG_EDX,
    UC_X86_REG_ESI,
    UC_X86_REG_EIP,
    UC_X86_REG_EFLAGS,
    UC_X86_REG_DS,
)

SECTOR = 2048
MEM_SIZE = 4 * 1024 * 1024
VGA_TEXT = 0xB8000

# Scancode set 1 tables (same layout as kernel/keyboard.c) for typing.
KEYMAP = [
    0, 27, "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "-", "=", "\b",
    "\t", "q", "w", "e", "r", "t", "y", "u", "i", "o", "p", "[", "]", "\n", 0,
    "a", "s", "d", "f", "g", "h", "j", "k", "l", ";", "'", "`", 0, "\\",
    "z", "x", "c", "v", "b", "n", "m", ",", ".", "/", 0, "*", 0, " ", 0,
] + [0] * 12 + ["7", "8", "9", "-", "4", "5", "6", "+", "1", "2", "3", "0", "."]

KEYMAP_SHIFT = [
    0, 27, "!", "@", "#", "$", "%", "^", "&", "*", "(", ")", "_", "+", "\b",
    "\t", "Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P", "{", "}", "\n", 0,
    "A", "S", "D", "F", "G", "H", "J", "K", "L", ":", '"', "~", 0, "|",
    "Z", "X", "C", "V", "B", "N", "M", "<", ">", "?", 0, "*", 0, " ", 0,
] + [0] * 12 + ["7", "8", "9", "-", "4", "5", "6", "+", "1", "2", "3", "0", "."]


def type_text(text):
    """Translate a string into PS/2 make/break scancodes."""
    codes = []
    for ch in text:
        if ch in KEYMAP:
            code = KEYMAP.index(ch)
            codes += [code, code | 0x80]
        elif ch in KEYMAP_SHIFT:
            code = KEYMAP_SHIFT.index(ch)
            codes += [0x2A, code, code | 0x80, 0xAA]
        else:
            raise ValueError(f"cannot type {ch!r}")
    return codes


class Machine:
    def __init__(self, iso):
        self.iso = iso
        self.uc = Uc(UC_ARCH_X86, UC_MODE_16)
        self.uc.mem_map(0, MEM_SIZE)

        boot = self._extract_boot_image()
        self.uc.mem_write(0x7C00, boot)
        self.uc.reg_write(UC_X86_REG_EDX, 0xE0)  # BIOS boot drive (CD)

        self.keys = []
        self.bios_out = bytearray()
        self.cmos_index = 0
        # Fake CMOS: 31.10.2026 14:30:00 (BCD, 24h), ~128 MiB of RAM.
        self.cmos = {
            0x00: 0x00, 0x02: 0x30, 0x04: 0x14,
            0x07: 0x31, 0x08: 0x10, 0x09: 0x26,
            0x0A: 0x26, 0x0B: 0x02,
            0x15: 0x80, 0x16: 0x02,   # 640 KiB base
            0x17: 0x00, 0x18: 0x3C,   # 15 MiB extended
            0x30: 0x00, 0x31: 0x07,   # 112 MiB above 16 MiB
        }
        self.idle_polls = 0
        self.script = []       # commands still to type
        self.snapshots = []    # screen capture each time the shell idles
        self.stop_requested = False
        self.poweroff = False
        self.rebooted = False
        self.boot_failed = False

        self.uc.hook_add(UC_HOOK_CODE, self._hook_code)

    def _extract_boot_image(self):
        bootrec = self.iso[17 * SECTOR : 18 * SECTOR]
        cat_lba = struct.unpack("<I", bootrec[71:75])[0]
        catalog = self.iso[cat_lba * SECTOR : (cat_lba + 1) * SECTOR]
        boot_lba = struct.unpack("<I", catalog[32 + 8 : 32 + 12])[0]
        return self.iso[boot_lba * SECTOR : boot_lba * SECTOR + SECTOR]

    # ---------------- fake hardware ----------------

    def _set_carry(self, on):
        flags = self.uc.reg_read(UC_X86_REG_EFLAGS)
        flags = (flags | 1) if on else (flags & ~1)
        self.uc.reg_write(UC_X86_REG_EFLAGS, flags)

    def _interrupt(self, intno):
        eax = self.uc.reg_read(UC_X86_REG_EAX)
        ah = (eax >> 8) & 0xFF

        if intno == 0x10:  # video
            if ah == 0x0E:
                self.bios_out.append(eax & 0xFF)
        elif intno == 0x13:  # disk
            if ah == 0x41:  # extensions present?
                self.uc.reg_write(UC_X86_REG_EBX, 0xAA55)
                self._set_carry(False)
            elif ah == 0x42:  # extended read
                ds = self.uc.reg_read(UC_X86_REG_DS)
                si = self.uc.reg_read(UC_X86_REG_ESI) & 0xFFFF
                dap = bytes(self.uc.mem_read(ds * 16 + si, 16))
                count = struct.unpack("<H", dap[2:4])[0]
                buf = struct.unpack("<H", dap[6:8])[0] * 16 + \
                    struct.unpack("<H", dap[4:6])[0]
                lba = struct.unpack("<I", dap[8:12])[0]
                data = self.iso[lba * SECTOR : lba * SECTOR + count * SECTOR]
                if len(data) < count * SECTOR:
                    self.uc.reg_write(UC_X86_REG_EAX, (eax & 0xFFFF00FF) | 0x100)
                    self._set_carry(True)
                else:
                    self.uc.mem_write(buf, data)
                    self.uc.reg_write(UC_X86_REG_EAX, eax & 0xFFFF00FF)
                    self._set_carry(False)
        elif intno == 0x15:  # misc (A20 enable etc.)
            self._set_carry(False)
        elif intno in (0x16, 0x18, 0x19):
            # "press any key to reboot" path == boot loader error.
            self.boot_failed = True
            self.stop_requested = True

    def _port_read(self, port, size):
        if port == 0x64:  # keyboard status
            if self.keys:
                self.idle_polls = 0
                return 0x01
            self.idle_polls += 1
            if self.idle_polls > 500:  # shell sits at the prompt
                self.snapshots.append("\n".join(self.screen()))
                if self.script:
                    self.keys += type_text(self.script.pop(0) + "\n")
                    self.idle_polls = 0
                else:
                    self.stop_requested = True
            return 0x00
        if port == 0x60:  # keyboard data
            return self.keys.pop(0) if self.keys else 0
        if port == 0x71:  # CMOS data
            return self.cmos.get(self.cmos_index & 0x7F, 0)
        return {1: 0xFF, 2: 0xFFFF}.get(size, 0xFFFFFFFF)

    def _port_write(self, port, size, value):
        if port == 0x70:
            self.cmos_index = value
        elif port == 0x64 and value == 0xFE:  # CPU reset pulse
            self.rebooted = True
            self.stop_requested = True
        elif port in (0x604, 0xB004, 0x4004):  # poweroff ports
            self.poweroff = True
            self.stop_requested = True

    @staticmethod
    def _decode_io(code):
        """Return ('in'|'out', size, port|None) for IN/OUT opcodes."""
        i = 0
        word = False
        if code and code[0] == 0x66:
            word = True
            i = 1
        if i >= len(code):
            return None
        op = code[i]
        size_word = 2 if word else 4
        if op == 0xE4 and len(code) > i + 1:
            return ("in", 1, code[i + 1])
        if op == 0xE5 and len(code) > i + 1:
            return ("in", size_word, code[i + 1])
        if op == 0xE6 and len(code) > i + 1:
            return ("out", 1, code[i + 1])
        if op == 0xE7 and len(code) > i + 1:
            return ("out", size_word, code[i + 1])
        if op == 0xEC:
            return ("in", 1, None)
        if op == 0xED:
            return ("in", size_word, None)
        if op == 0xEE:
            return ("out", 1, None)
        if op == 0xEF:
            return ("out", size_word, None)
        return None

    def _hook_code(self, uc, address, size, _user_data):
        code = bytes(uc.mem_read(address, size))
        handled = False

        if code and code[0] == 0xCD and len(code) >= 2:  # INT n
            self._interrupt(code[1])
            handled = True
        else:
            io = self._decode_io(code)
            if io is not None:
                direction, data_size, port = io
                eax = uc.reg_read(UC_X86_REG_EAX)
                if port is None:
                    port = uc.reg_read(UC_X86_REG_EDX) & 0xFFFF
                if direction == "in":
                    value = self._port_read(port, data_size)
                    if data_size == 1:
                        eax = (eax & ~0xFF) | (value & 0xFF)
                    elif data_size == 2:
                        eax = (eax & ~0xFFFF) | (value & 0xFFFF)
                    else:
                        eax = value & 0xFFFFFFFF
                    uc.reg_write(UC_X86_REG_EAX, eax)
                else:
                    mask = (1 << (data_size * 8)) - 1
                    self._port_write(port, data_size, eax & mask)
                handled = True

        if handled:
            uc.reg_write(UC_X86_REG_EIP, uc.reg_read(UC_X86_REG_EIP) + size)
        if self.stop_requested:
            self.stop_requested = False
            uc.emu_stop()

    # ---------------- running ----------------

    def run(self, script):
        """Boot and feed the given shell commands, one per prompt."""
        self.script = list(script)
        self.idle_polls = 0
        try:
            self.uc.emu_start(0x7C00, 0xFFFFFFFF, timeout=120_000_000)
        except UcError as exc:
            pc = self.uc.reg_read(UC_X86_REG_EIP)
            raise RuntimeError(f"emulation error at PC={pc:#x}: {exc}") from exc

    def screen(self):
        raw = bytes(self.uc.mem_read(VGA_TEXT, 80 * 25 * 2))
        lines = []
        for row in range(25):
            line = "".join(chr(raw[(row * 80 + col) * 2]) for col in range(80))
            lines.append(line.rstrip())
        while lines and not lines[-1]:
            lines.pop()
        return lines



def main():
    if len(sys.argv) != 2:
        sys.exit("usage: emutest.py <image.iso>")

    with open(sys.argv[1], "rb") as f:
        iso = f.read()

    machine = Machine(iso)
    failures = []

    def check(name, cond):
        print(("  OK   " if cond else "  FAIL ") + name)
        if not cond:
            failures.append(name)

    commands = [
        "version",
        "cpu",
        "mem",
        "date",
        "echo hello-yoro-123",
        "unknowncmd",
        "help",
        "shutdown",
    ]

    print("Booting YoroOS in Unicorn emulator...\n")
    machine.run(commands)

    # snapshots[i] is the screen while the shell waited for command i:
    # snapshots[0] = right after boot, snapshots[1] = after 'version', ...
    def snap(i):
        return machine.snapshots[i] if i < len(machine.snapshots) else ""

    check("boot loader did not hit an error path", not machine.boot_failed)
    check("boot loader printed its banner via BIOS",
          b"YoroOS Loader" in machine.bios_out and b"OK" in machine.bios_out)
    check("kernel banner on screen", "YoroOS version" in snap(0))
    check("shell prompt shown", "yoro@YoroOS:~$" in snap(0))
    check("'version' output", "YoroOS 0.2" in snap(1))
    check("'cpu' output", "CPU vendor:" in snap(2))
    check("'mem' output", "Memory:" in snap(3) and "MiB" in snap(3))
    check("'date' output (fake RTC = 31.10.2026 14:30)",
          "31.10.2026 14:30" in snap(4))
    check("'echo' output", "hello-yoro-123" in snap(5))
    check("unknown command handled", "Unknown command" in snap(6))
    check("'help' output",
          "Available commands" in snap(7) or "color <0-15>" in snap(7))
    check("'shutdown' powered the machine off", machine.poweroff)

    print("\n--- screen right after boot ---")
    for line in snap(0).splitlines():
        print("| " + line)
    print("--------------------------------")

    print("\n--- final screen ---")
    for line in machine.screen():
        print("| " + line)
    print("--------------------")

    if failures:
        print(f"\nFAILED: {len(failures)} check(s)")
        sys.exit(1)
    print("\nAll emulation checks passed. YoroOS boots and the shell works.")


if __name__ == "__main__":
    main()
