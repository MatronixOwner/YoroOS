/* Linker script for the YoroOS UEFI application (gnu-efi style). */
OUTPUT_FORMAT("elf64-x86-64")
OUTPUT_ARCH(i386:x86-64)
ENTRY(efi_main)

SECTIONS
{
    . = 0;

    .text : {
        *(.text)
        *(.text.*)
        *(.gnu.linkonce.t.*)
    }

    . = ALIGN(4096);

    .sdata : {
        *(.got.plt)
        *(.got)
        *(.sdata)
        *(.sbss)
    }

    .data : {
        *(.data)
        *(.data.*)
        *(.rodata)
        *(.rodata.*)
        *(.bss)
        *(.bss.*)
        *(COMMON)
    }

    .dynamic : { *(.dynamic) }
    .dynsym  : { *(.dynsym) }
    .dynstr  : { *(.dynstr) }
    .rel     : { *(.rel) *(.rel.*) }
    .rela    : { *(.rela) *(.rela.*) }
    .reloc   : { *(.reloc) }

    /DISCARD/ : {
        *(.note*)
        *(.comment)
        *(.eh_frame*)
    }
}
