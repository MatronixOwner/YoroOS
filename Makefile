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
KERNEL_OBJ := $(patsubst kernel/%.c,$(BUILD)/%.o,$(KERNEL_C)) $(BUILD)/entry.o $(BUILD)/yorofs.o

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

# ---- shared volatile filesystem prototype ----
$(BUILD)/yorofs.o: common/yorofs.c include/yorofs.h | $(BUILD)
	$(CC) $(CFLAGS) -c $< -o $@

# ---- kernel ----
$(BUILD)/%.o: kernel/%.c | $(BUILD)
	$(CC) $(CFLAGS) -c $< -o $@

$(BUILD)/entry.o: kernel/entry.S | $(BUILD)
	$(AS) --32 $< -o $@

$(BUILD)/kernel.elf: $(KERNEL_OBJ) linker.ld
	$(LD) -m elf_i386 -T linker.ld -o $@ $(KERNEL_OBJ)

$(BUILD)/kernel.bin: $(BUILD)/kernel.elf
	$(OBJCOPY) -O binary $< $@

# ---- UEFI application (BOOTX64.EFI) for Hyper-V Gen2 / UEFI ----
EFI_CFLAGS := -m64 -std=gnu11 -ffreestanding -fpic -fshort-wchar \
              -mno-red-zone -fno-stack-protector -nostdlib \
              -Wall -Wextra -O2 -Iinclude

$(BUILD)/efi_main.o: efi/efi_main.c efi/efi.h | $(BUILD)
	$(CC) $(EFI_CFLAGS) -c $< -o $@

$(BUILD)/efi_yorofs.o: common/yorofs.c include/yorofs.h | $(BUILD)
	$(CC) $(EFI_CFLAGS) -c $< -o $@

$(BUILD)/BOOTX64.so: $(BUILD)/efi_main.o $(BUILD)/efi_yorofs.o efi/efi.lds
	$(LD) -shared -Bsymbolic -nostdlib -znocombreloc -T efi/efi.lds -o $@ $(BUILD)/efi_main.o $(BUILD)/efi_yorofs.o

$(BUILD)/BOOTX64.EFI: $(BUILD)/BOOTX64.so
	$(OBJCOPY) -j .text -j .sdata -j .data -j .dynamic -j .dynsym \
	    -j .dynstr -j .rel -j .rela -j .reloc \
	    --target=efi-app-x86-64 $< $@

$(BUILD)/efiboot.img: $(BUILD)/BOOTX64.EFI tools/mkefiboot.py
	$(PYTHON) tools/mkefiboot.py $(BUILD)/BOOTX64.EFI $@

# ---- ISO image (ISO9660 + El Torito BIOS+UEFI, built by our own tool) ----
$(ISO): $(BUILD)/boot.bin $(BUILD)/kernel.bin $(BUILD)/efiboot.img tools/mkiso.py
	$(PYTHON) tools/mkiso.py $(BUILD)/boot.bin $(BUILD)/kernel.bin $(BUILD)/efiboot.img $@
	$(PYTHON) tools/verify_iso.py $@

run: $(ISO)
	qemu-system-i386 -cdrom $(ISO) -boot d -m 64

verify: $(ISO)
	$(PYTHON) tools/verify_iso.py $(ISO)

clean:
	rm -rf $(BUILD)

.PHONY: test
test: | $(BUILD)
	$(CC) -std=c11 -Wall -Wextra -Werror -iquote include common/yorofs.c tests/yorofs_test.c -o $(BUILD)/yorofs-test
	$(BUILD)/yorofs-test

# Separate experimental UEFI x86-64 graphical image. BIOS retains the old shell.
NATIVE64_FLAGS := $(EFI_CFLAGS) -mno-sse -mno-sse2 -mno-mmx -msoft-float -fno-ident -fno-asynchronous-unwind-tables -fno-unwind-tables
$(BUILD)/graphics_boot.o: efi/graphics_boot.c efi/efi.h native64/bootinfo.h | $(BUILD)
	$(CC) $(NATIVE64_FLAGS) -c $< -o $@
$(BUILD)/native64_kernel.o: native64/kernel.c native64/bootinfo.h | $(BUILD)
	$(CC) $(NATIVE64_FLAGS) -c $< -o $@
$(BUILD)/native64_render.o: native64/render.c native64/bootinfo.h | $(BUILD)
	$(CC) $(NATIVE64_FLAGS) -c $< -o $@
$(BUILD)/native64_entry.o: native64/entry.S | $(BUILD)
	$(CC) -m64 -c $< -o $@
$(BUILD)/graphics.EFI: $(BUILD)/graphics_boot.o $(BUILD)/native64_kernel.o $(BUILD)/native64_render.o $(BUILD)/native64_entry.o
	$(LD) -mi386pep --subsystem 10 --entry efi_main --no-insert-timestamp -o $@ $(filter %.o,$^)
$(BUILD)/graphics-efiboot.img: $(BUILD)/graphics.EFI tools/mkefiboot.py
	$(PYTHON) tools/mkefiboot.py $< $@
$(BUILD)/yoroos-native-graphical.iso: $(BUILD)/boot.bin $(BUILD)/kernel.bin $(BUILD)/graphics-efiboot.img tools/mkiso.py
	$(PYTHON) tools/mkiso.py $(BUILD)/boot.bin $(BUILD)/kernel.bin $(BUILD)/graphics-efiboot.img $@
	$(PYTHON) tools/verify_iso.py $@
.PHONY: graphics-iso test-graphics
graphics-iso: $(BUILD)/yoroos-native-graphical.iso
test-graphics: | $(BUILD)
	$(CC) -std=c11 -Wall -Wextra -Werror -fsanitize=address,undefined -iquote native64 native64/render.c tests/native64_render_test.c -o $(BUILD)/native64-render-test
	$(BUILD)/native64-render-test
