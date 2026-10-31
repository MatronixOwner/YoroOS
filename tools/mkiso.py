#!/usr/bin/env python3
"""
YoroOS ISO image builder.

Creates a bootable ISO9660 image with an El Torito boot record
(BIOS, no-emulation) without any external tools (no xorriso needed).

The image contains two files:
    BOOT.BIN    - 2048-byte boot image (real-mode loader, first 512 used)
    KERNEL.BIN  - the kernel binary

Before writing, the loader binary is patched: the magic dwords
0xDEADBEEF / 0xCAFEBABE inside BOOT.BIN are replaced with the LBA and
sector count of KERNEL.BIN inside the ISO, so the loader knows where
to read the kernel from.

Usage: mkiso.py <boot.bin> <kernel.bin> <output.iso>
"""

import struct
import sys
import datetime

SECTOR = 2048

# Fixed ISO layout (LBA numbers).
LBA_PVD = 16
LBA_BOOTREC = 17
LBA_TERM = 18
LBA_PATH_L = 19
LBA_PATH_M = 20
LBA_ROOTDIR = 21
LBA_BOOTCAT = 22
LBA_BOOTIMG = 23
LBA_KERNEL = 24


def both16(value):
    return struct.pack("<H", value) + struct.pack(">H", value)


def both32(value):
    return struct.pack("<I", value) + struct.pack(">I", value)


def dir_record(lba, size, flags, name, now):
    """ISO9660 directory record. name: b'\\x00'='.', b'\\x01'='..' or ASCII."""
    length = 33 + len(name)
    if length % 2:
        length += 1
    rec = bytearray(length)
    rec[0] = length
    rec[1] = 0
    rec[2:10] = both32(lba)
    rec[10:18] = both32(size)
    rec[18:25] = bytes(
        [now.year - 1900, now.month, now.day, now.hour, now.minute, now.second, 0]
    )
    rec[25] = flags
    rec[28:32] = both16(1)
    rec[32] = len(name)
    rec[33 : 33 + len(name)] = name
    return bytes(rec)


def volume_datetime(now):
    """17-byte volume descriptor timestamp (GMT)."""
    return (now.strftime("%Y%m%d%H%M%S") + "00").encode() + b"\x00"


def build_pvd(total_sectors, path_table_size, now):
    pvd = bytearray(SECTOR)
    pvd[0] = 1
    pvd[1:6] = b"CD001"
    pvd[6] = 1
    pvd[8:40] = b"YOROOS".ljust(32, b" ")          # system id
    pvd[40:72] = b"YOROOS".ljust(32, b" ")         # volume id
    pvd[80:88] = both32(total_sectors)             # volume space size
    pvd[120:124] = both16(1)                       # volume set size
    pvd[124:128] = both16(1)                       # volume sequence number
    pvd[128:132] = both16(SECTOR)                  # logical block size
    pvd[132:140] = both32(path_table_size)
    pvd[140:144] = struct.pack("<I", LBA_PATH_L)
    pvd[144:148] = struct.pack("<I", 0)
    pvd[148:152] = struct.pack(">I", LBA_PATH_M)
    pvd[152:156] = struct.pack(">I", 0)
    root_rec = dir_record(LBA_ROOTDIR, SECTOR, 2, b"\x00", now)
    pvd[156 : 156 + len(root_rec)] = root_rec
    for start, length in ((190, 128), (318, 128), (446, 128), (574, 128)):
        pvd[start : start + length] = b" ".ljust(length, b" ")
    pvd[574:580] = b"YOROOS"                       # application id
    for start, length in ((702, 37), (739, 37), (776, 37)):
        pvd[start : start + length] = b" ".ljust(length, b" ")
    stamp = volume_datetime(now)
    pvd[813:830] = stamp                           # creation
    pvd[830:847] = stamp                           # modification
    pvd[847:864] = b"0000000000000000\x00"         # expiration (none)
    pvd[864:881] = stamp                           # effective
    pvd[881] = 1                                   # file structure version
    return bytes(pvd)


def build_boot_record():
    rec = bytearray(SECTOR)
    rec[0] = 0
    rec[1:6] = b"CD001"
    rec[6] = 1
    rec[7:39] = b"EL TORITO SPECIFICATION".ljust(32, b"\x00")
    rec[71:75] = struct.pack("<I", LBA_BOOTCAT)
    return bytes(rec)


def build_terminator():
    rec = bytearray(SECTOR)
    rec[0] = 255
    rec[1:6] = b"CD001"
    rec[6] = 1
    return bytes(rec)


def build_path_table(big_endian):
    fmt = ">" if big_endian else "<"
    table = bytearray()
    table += bytes([1, 0])                          # name length, ext attr len
    table += struct.pack(fmt + "I", LBA_ROOTDIR)    # extent
    table += struct.pack(fmt + "H", 1)              # parent index
    table += b"\x00"                                # root name
    table += b"\x00"                                # padding (odd name length)
    sector = bytearray(SECTOR)
    sector[: len(table)] = table
    return bytes(sector), len(table)


def build_root_dir(boot_size, kernel_size, now):
    sector = bytearray(SECTOR)
    records = b"".join(
        [
            dir_record(LBA_ROOTDIR, SECTOR, 2, b"\x00", now),
            dir_record(LBA_ROOTDIR, SECTOR, 2, b"\x01", now),
            dir_record(LBA_BOOTIMG, boot_size, 0, b"BOOT.BIN;1", now),
            dir_record(LBA_KERNEL, kernel_size, 0, b"KERNEL.BIN;1", now),
        ]
    )
    sector[: len(records)] = records
    return bytes(sector)


def build_boot_catalog():
    catalog = bytearray(SECTOR)

    # Validation entry.
    ve = bytearray(32)
    ve[0] = 1                                        # header id
    ve[1] = 0                                        # platform: x86
    ve[4:28] = b"YoroOS".ljust(24, b"\x00")
    ve[30] = 0x55
    ve[31] = 0xAA
    words = struct.unpack("<16H", bytes(ve))
    checksum = (-sum(words)) & 0xFFFF
    ve[28:30] = struct.pack("<H", checksum)
    catalog[0:32] = ve

    # Initial/default entry: bootable, no emulation.
    de = bytearray(32)
    de[0] = 0x88                                     # bootable
    de[1] = 0                                        # no emulation
    de[2:4] = struct.pack("<H", 0)                   # load segment (0 => 0x7C0)
    de[4] = 0                                        # system type
    de[6:8] = struct.pack("<H", 4)                   # 4*512 = 2048 bytes loaded
    de[8:12] = struct.pack("<I", LBA_BOOTIMG)
    catalog[32:64] = de

    return bytes(catalog)


def patch_boot_image(boot, kernel_lba, kernel_sectors):
    boot = bytearray(boot)
    magic_lba = struct.pack("<I", 0xDEADBEEF)
    magic_cnt = struct.pack("<I", 0xCAFEBABE)
    if boot.count(magic_lba) != 1 or boot.count(magic_cnt) != 1:
        sys.exit("mkiso: patch magics not found exactly once in boot image")
    off = boot.index(magic_lba)
    boot[off : off + 4] = struct.pack("<I", kernel_lba)
    off = boot.index(magic_cnt)
    boot[off : off + 4] = struct.pack("<I", kernel_sectors)
    if bytes(boot[510:512]) != b"\x55\xaa":
        sys.exit("mkiso: boot image missing 0xAA55 signature")
    return bytes(boot)


def main():
    if len(sys.argv) != 4:
        sys.exit(__doc__.splitlines()[-3].strip())

    boot_path, kernel_path, out_path = sys.argv[1:]

    with open(boot_path, "rb") as f:
        boot = f.read()
    with open(kernel_path, "rb") as f:
        kernel = f.read()

    if len(boot) != SECTOR:
        sys.exit(f"mkiso: boot image must be {SECTOR} bytes, got {len(boot)}")

    kernel_sectors = (len(kernel) + SECTOR - 1) // SECTOR
    total_sectors = LBA_KERNEL + kernel_sectors
    now = datetime.datetime.now()

    boot = patch_boot_image(boot, LBA_KERNEL, kernel_sectors)
    kernel_padded = kernel + b"\x00" * (kernel_sectors * SECTOR - len(kernel))

    path_l, path_table_size = build_path_table(big_endian=False)
    path_m, _ = build_path_table(big_endian=True)

    image = bytearray(total_sectors * SECTOR)

    def put(lba, data):
        image[lba * SECTOR : lba * SECTOR + len(data)] = data

    put(LBA_PVD, build_pvd(total_sectors, path_table_size, now))
    put(LBA_BOOTREC, build_boot_record())
    put(LBA_TERM, build_terminator())
    put(LBA_PATH_L, path_l)
    put(LBA_PATH_M, path_m)
    put(LBA_ROOTDIR, build_root_dir(len(boot), len(kernel), now))
    put(LBA_BOOTCAT, build_boot_catalog())
    put(LBA_BOOTIMG, boot)
    put(LBA_KERNEL, kernel_padded)

    with open(out_path, "wb") as f:
        f.write(image)

    print(f"mkiso: wrote {out_path}")
    print(f"  total size : {len(image)} bytes ({total_sectors} sectors)")
    print(f"  boot image : LBA {LBA_BOOTIMG}, {len(boot)} bytes")
    print(f"  kernel     : LBA {LBA_KERNEL}, {len(kernel)} bytes"
          f" ({kernel_sectors} sectors)")


if __name__ == "__main__":
    main()
