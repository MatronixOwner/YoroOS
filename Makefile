# YoroOS build system.
# Requires only: gcc, binutils (as/ld/objcopy), python3. That's it.

CC      := gcc
AS      := as
LD      := ld
OBJCOPY := objcopy
PYTHON  := python3

BUILD := build
ISO   := $(BUILD)/yoroos.iso

CFLAGS := -m32 -std=gnu11 -ffreestanding -fno-pie -fno-pic \
          -fno-stack-protector -mno-sse -mno-sse2 -mno-mmx \
          -nostdlib -Wall -Wextra -O2 -Iinclude

KERNEL_C := $(wildcard kernel/*.c)
KERNEL_OBJ := $(patsubst kernel/%.c,$(BUILD)/%.o,$(KERNEL_C)) $(BUILD)/entry.o

.PHONY: all iso clean run verify
all: iso

iso: $(ISO)

$(BUILD):
	mkdir -p $(BUILD)

# ---- boot loader: 16-bit real-mode code with 0xAA55 signature ----
$(BUILD)/boot.o: boot/boot.S | $(BUILD)
	$(AS) --32 $< -o $@

$(BUILD)/boot.bin: $(BUILD)/boot.o
	$(LD) -m elf_i386 -Ttext 0x7C00 --oformat binary -o $@ $<
	truncate -s 2048 $@

# ---- kernel ----
$(BUILD)/%.o: kernel/%.c | $(BUILD)
	$(CC) $(CFLAGS) -c $< -o $@

$(BUILD)/entry.o: kernel/entry.S | $(BUILD)
	$(AS) --32 $< -o $@

$(BUILD)/kernel.elf: $(KERNEL_OBJ) linker.ld
	$(LD) -m elf_i386 -T linker.ld -o $@ $(KERNEL_OBJ)

$(BUILD)/kernel.bin: $(BUILD)/kernel.elf
	$(OBJCOPY) -O binary $< $@

# ---- ISO image (ISO9660 + El Torito, built by our own tool) ----
$(ISO): $(BUILD)/boot.bin $(BUILD)/kernel.bin tools/mkiso.py
	$(PYTHON) tools/mkiso.py $(BUILD)/boot.bin $(BUILD)/kernel.bin $@
	$(PYTHON) tools/verify_iso.py $@

run: $(ISO)
	qemu-system-i386 -cdrom $(ISO) -boot d -m 64

verify: $(ISO)
	$(PYTHON) tools/verify_iso.py $(ISO)

clean:
	rm -rf $(BUILD)
