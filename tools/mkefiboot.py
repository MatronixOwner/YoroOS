#!/usr/bin/env python3
"""
Build the EFI boot image for YoroOS: a 1.44 MiB FAT12 disk image that
contains a single file, \\EFI\\BOOT\\BOOTX64.EFI.

UEFI firmware booting from CD (El Torito platform 0xEF) mounts this
image as a virtual floppy/ESP and runs BOOTX64.EFI from it.

Usage: mkefiboot.py <BOOTX64.EFI> <output.img>
"""

import struct
import sys

SECTOR = 512
TOTAL_SECTORS = 2880            # 1.44 MiB
FAT_SECTORS = 9
ROOT_ENTRIES = 224
ROOT_SECTORS = ROOT_ENTRIES * 32 // SECTOR      # 14
DATA_START = 1 + 2 * FAT_SECTORS + ROOT_SECTORS  # sector 33

# DOS date/time stamps (fixed values, only cosmetic).
DOS_DATE = ((2026 - 1980) << 9) | (10 << 5) | 31
DOS_TIME = 12 << 11


def cluster_offset(n):
    return (DATA_START + (n - 2)) * SECTOR


def fat12_set(fat, n, value):
    off = n * 3 // 2
    if n % 2 == 0:
        fat[off] = value & 0xFF
        fat[off + 1] = (fat[off + 1] & 0xF0) | ((value >> 8) & 0x0F)
    else:
        fat[off] = (fat[off] & 0x0F) | ((value << 4) & 0xF0)
        fat[off + 1] = (value >> 4) & 0xFF


def dir_entry(name11, attr, cluster, size):
    e = bytearray(32)
    e[0:11] = name11
    e[11] = attr
    struct.pack_into("<H", e, 14, DOS_TIME)
    struct.pack_into("<H", e, 16, DOS_DATE)
    struct.pack_into("<H", e, 18, DOS_DATE)
    struct.pack_into("<H", e, 22, DOS_TIME)
    struct.pack_into("<H", e, 24, DOS_DATE)
    struct.pack_into("<H", e, 26, cluster)
    struct.pack_into("<I", e, 28, size)
    return bytes(e)


def build_boot_sector():
    bs = bytearray(SECTOR)
    bs[0:3] = b"\xEB\x3C\x90"
    bs[3:11] = b"YOROOS  "
    struct.pack_into("<H", bs, 11, SECTOR)       # bytes per sector
    bs[13] = 1                                   # sectors per cluster
    struct.pack_into("<H", bs, 14, 1)            # reserved sectors
    bs[16] = 2                                   # number of FATs
    struct.pack_into("<H", bs, 17, ROOT_ENTRIES)
    struct.pack_into("<H", bs, 19, TOTAL_SECTORS)
    bs[21] = 0xF0                                # media descriptor
    struct.pack_into("<H", bs, 22, FAT_SECTORS)
    struct.pack_into("<H", bs, 24, 18)           # sectors per track
    struct.pack_into("<H", bs, 26, 2)            # heads
    bs[36] = 0                                   # drive number
    bs[38] = 0x29                                # extended boot signature
    struct.pack_into("<I", bs, 39, 0x20261031)   # volume serial
    bs[43:54] = b"YOROOS EFI "                   # volume label
    bs[54:62] = b"FAT12   "                      # fs type
    bs[510:512] = b"\x55\xAA"
    return bytes(bs)


def main():
    if len(sys.argv) != 3:
        sys.exit("usage: mkefiboot.py <BOOTX64.EFI> <output.img>")

    with open(sys.argv[1], "rb") as f:
        efi = f.read()
    if not efi.startswith(b"MZ"):
        sys.exit("mkefiboot: input does not look like a PE/EFI binary")

    img = bytearray(TOTAL_SECTORS * SECTOR)
    img[0:SECTOR] = build_boot_sector()

    # Clusters: 2 = \EFI, 3 = \EFI\BOOT, 4.. = BOOTX64.EFI data.
    file_clusters = (len(efi) + SECTOR - 1) // SECTOR
    last_cluster = 4 + file_clusters - 1
    if cluster_offset(last_cluster) + SECTOR > len(img):
        sys.exit("mkefiboot: BOOTX64.EFI does not fit in the image")

    fat = bytearray(FAT_SECTORS * SECTOR)
    fat12_set(fat, 0, 0xFF0)
    fat12_set(fat, 1, 0xFFF)
    fat12_set(fat, 2, 0xFFF)
    fat12_set(fat, 3, 0xFFF)
    for c in range(4, last_cluster + 1):
        fat12_set(fat, c, 0xFFF if c == last_cluster else c + 1)
    img[SECTOR:SECTOR + len(fat)] = fat
    img[SECTOR + len(fat):SECTOR + 2 * len(fat)] = fat

    # Root directory: volume label + EFI directory.
    root = bytearray()
    root += dir_entry(b"YOROOS EFI ", 0x08, 0, 0)
    root += dir_entry(b"EFI        ", 0x10, 2, 0)
    root_off = (1 + 2 * FAT_SECTORS) * SECTOR
    img[root_off:root_off + len(root)] = root

    # \EFI directory.
    efi_dir = bytearray(SECTOR)
    efi_dir[0:32] = dir_entry(b".          ", 0x10, 2, 0)
    efi_dir[32:64] = dir_entry(b"..         ", 0x10, 0, 0)
    efi_dir[64:96] = dir_entry(b"BOOT       ", 0x10, 3, 0)
    img[cluster_offset(2):cluster_offset(2) + SECTOR] = efi_dir

    # \EFI\BOOT directory.
    boot_dir = bytearray(SECTOR)
    boot_dir[0:32] = dir_entry(b".          ", 0x10, 3, 0)
    boot_dir[32:64] = dir_entry(b"..         ", 0x10, 2, 0)
    boot_dir[64:96] = dir_entry(b"BOOTX64 EFI", 0x20, 4, len(efi))
    img[cluster_offset(3):cluster_offset(3) + SECTOR] = boot_dir

    # File data.
    img[cluster_offset(4):cluster_offset(4) + len(efi)] = efi

    with open(sys.argv[2], "wb") as f:
        f.write(img)

    print(f"mkefiboot: wrote {sys.argv[2]} ({len(img)} bytes), "
          f"BOOTX64.EFI = {len(efi)} bytes in {file_clusters} clusters")


if __name__ == "__main__":
    main()
