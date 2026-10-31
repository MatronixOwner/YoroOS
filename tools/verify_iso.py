#!/usr/bin/env python3
"""
Verify a YoroOS ISO image: parse ISO9660 + El Torito structures and
cross-check that the boot loader points at the right kernel location.

Usage: verify_iso.py <image.iso>
Exit code 0 = all checks passed.
"""

import struct
import sys

SECTOR = 2048


def main():
    if len(sys.argv) != 2:
        sys.exit("usage: verify_iso.py <image.iso>")

    with open(sys.argv[1], "rb") as f:
        img = f.read()

    def sector(lba):
        return img[lba * SECTOR : (lba + 1) * SECTOR]

    errors = []

    def check(cond, msg):
        print(("  OK   " if cond else "  FAIL ") + msg)
        if not cond:
            errors.append(msg)

    print(f"Verifying {sys.argv[1]} ({len(img)} bytes)")
    check(len(img) % SECTOR == 0, "image size is a multiple of 2048")

    # Volume descriptors.
    pvd = sector(16)
    check(pvd[0] == 1 and pvd[1:6] == b"CD001", "primary volume descriptor")
    check(pvd[40:46] == b"YOROOS", "volume id is YOROOS")
    total = struct.unpack("<I", pvd[80:84])[0]
    check(total * SECTOR == len(img), f"volume size matches file ({total} sectors)")

    bootrec = sector(17)
    check(
        bootrec[0] == 0 and bootrec[7:30] == b"EL TORITO SPECIFICATION",
        "El Torito boot record descriptor",
    )
    check(sector(18)[0] == 255, "volume descriptor terminator")

    catalog_lba = struct.unpack("<I", bootrec[71:75])[0]
    catalog = sector(catalog_lba)

    # Validation entry: all 16-bit words must sum to zero.
    words = struct.unpack("<16H", catalog[0:32])
    check(sum(words) & 0xFFFF == 0, "boot catalog validation checksum")
    check(catalog[30] == 0x55 and catalog[31] == 0xAA, "validation entry key bytes")

    # Default boot entry.
    entry = catalog[32:64]
    check(entry[0] == 0x88, "default entry is marked bootable")
    check(entry[1] == 0, "boot media type: no emulation")
    load_count = struct.unpack("<H", entry[6:8])[0]
    boot_lba = struct.unpack("<I", entry[8:12])[0]
    check(load_count == 4, "boot image load size = 2048 bytes")

    boot = sector(boot_lba)
    check(boot[510:512] == b"\x55\xaa", "boot sector 0xAA55 signature")

    # Find where mkiso patched the kernel pointer (search for the pair
    # is not possible after patching, so re-derive from the root dir).
    root_lba = struct.unpack("<I", pvd[156 + 2 : 156 + 6])[0]
    root = sector(root_lba)
    files = {}
    off = 0
    while off < SECTOR and root[off] != 0:
        rec_len = root[off]
        rec = root[off : off + rec_len]
        name_len = rec[32]
        name = bytes(rec[33 : 33 + name_len])
        if name not in (b"\x00", b"\x01"):
            files[name] = (
                struct.unpack("<I", rec[2:6])[0],
                struct.unpack("<I", rec[10:14])[0],
            )
        off += rec_len

    check(b"BOOT.BIN;1" in files, "BOOT.BIN present in root directory")
    check(b"KERNEL.BIN;1" in files, "KERNEL.BIN present in root directory")

    if b"KERNEL.BIN;1" in files and b"BOOT.BIN;1" in files:
        k_lba, k_size = files[b"KERNEL.BIN;1"]
        b_lba, _ = files[b"BOOT.BIN;1"]
        check(b_lba == boot_lba, "boot catalog LBA matches BOOT.BIN location")

        # The two patched dwords sit next to each other in the boot image:
        # kernel LBA followed by kernel sector count.
        k_sectors = (k_size + SECTOR - 1) // SECTOR
        needle = struct.pack("<II", k_lba, k_sectors)
        check(
            needle in boot,
            f"loader patched with kernel location (LBA {k_lba}, {k_sectors} sectors)",
        )

        kernel = img[k_lba * SECTOR : k_lba * SECTOR + k_size]
        check(len(kernel) == k_size and k_size > 0,
              f"kernel readable ({k_size} bytes)")
        # _start begins with segment loads: 66 B8 10 00 (mov ax, 0x10)
        check(kernel[0:4] == b"\x66\xb8\x10\x00",
              "kernel starts with entry code (mov ax, 0x10)")

    # --- UEFI (El Torito platform 0xEF) ---
    check(b"EFIBOOT.IMG;1" in files, "EFIBOOT.IMG present in root directory")
    sh = catalog[64:96]
    ee = catalog[96:128]
    check(sh[0] == 0x91 and sh[1] == 0xEF, "UEFI section header (platform 0xEF)")
    check(struct.unpack("<H", sh[2:4])[0] == 1, "one UEFI boot entry")
    check(ee[0] == 0x88, "UEFI entry is marked bootable")

    if b"EFIBOOT.IMG;1" in files:
        e_lba, e_size = files[b"EFIBOOT.IMG;1"]
        efi_cat_lba = struct.unpack("<I", ee[8:12])[0]
        efi_cnt512 = struct.unpack("<H", ee[6:8])[0]
        check(efi_cat_lba == e_lba, "UEFI catalog LBA matches EFIBOOT.IMG")
        check(efi_cnt512 * 512 == e_size, "UEFI image size matches catalog")

        fat_img = img[e_lba * SECTOR : e_lba * SECTOR + e_size]
        check(fat_img[510:512] == b"\x55\xaa", "FAT boot sector signature")
        check(fat_img[54:62] == b"FAT12   ", "FAT12 filesystem type")

        bps = struct.unpack("<H", fat_img[11:13])[0]
        spc = fat_img[13]
        reserved = struct.unpack("<H", fat_img[14:16])[0]
        nfats = fat_img[16]
        root_entries = struct.unpack("<H", fat_img[17:19])[0]
        fat_size = struct.unpack("<H", fat_img[22:24])[0]
        fat = fat_img[reserved * bps : (reserved + fat_size) * bps]
        root_off = (reserved + nfats * fat_size) * bps
        data_off = root_off + root_entries * 32

        def fat12_get(n):
            off = n * 3 // 2
            if n % 2 == 0:
                return fat[off] | ((fat[off + 1] & 0x0F) << 8)
            return (fat[off] >> 4) | (fat[off + 1] << 4)

        def cluster_bytes(n):
            start = data_off + (n - 2) * spc * bps
            return fat_img[start : start + spc * bps]

        def read_chain(start_cluster, size):
            data = bytearray()
            n = start_cluster
            while 2 <= n < 0xFF8:
                data += cluster_bytes(n)
                n = fat12_get(n)
            return bytes(data[:size])

        def find(dir_bytes, name11):
            for off in range(0, len(dir_bytes), 32):
                e = dir_bytes[off : off + 32]
                if len(e) < 32 or e[0] == 0:
                    return None
                if bytes(e[0:11]) == name11:
                    return (struct.unpack("<H", e[26:28])[0],
                            struct.unpack("<I", e[28:32])[0], e[11])
            return None

        root_dir = fat_img[root_off:data_off]
        efi_dir = find(root_dir, b"EFI        ")
        check(efi_dir is not None, "FAT: \\EFI directory exists")
        boot_dir = (find(read_chain(efi_dir[0], spc * bps), b"BOOT       ")
                    if efi_dir else None)
        check(boot_dir is not None, "FAT: \\EFI\\BOOT directory exists")
        app = (find(read_chain(boot_dir[0], spc * bps), b"BOOTX64 EFI")
               if boot_dir else None)
        check(app is not None, "FAT: BOOTX64.EFI exists")
        if app:
            pe = read_chain(app[0], app[1])
            check(pe[:2] == b"MZ" and app[1] > 0,
                  f"BOOTX64.EFI readable ({app[1]} bytes)")
            pe_off = struct.unpack("<I", pe[0x3C:0x40])[0]
            check(pe[pe_off:pe_off + 4] == b"PE\x00\x00", "PE signature")
            machine = struct.unpack("<H", pe[pe_off + 4 : pe_off + 6])[0]
            check(machine == 0x8664, "PE machine type is x86-64")
            subsystem = struct.unpack(
                "<H", pe[pe_off + 24 + 68 : pe_off + 24 + 70])[0]
            check(subsystem == 10, "PE subsystem is EFI application")

    if errors:
        print(f"\nFAILED: {len(errors)} check(s) did not pass.")
        sys.exit(1)
    print("\nAll checks passed. Image should boot (BIOS / El Torito).")


if __name__ == "__main__":
    main()
