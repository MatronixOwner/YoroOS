ENTRY(_start)

SECTIONS
{
    /* The boot loader loads the kernel at physical 0x10000. */
    . = 0x10000;

    .text : {
        *(.text.entry)   /* _start must be the very first byte */
        *(.text*)
    }

    .rodata : {
        *(.rodata*)
    }

    .data : {
        *(.data*)
    }

    .bss : {
        _bss_start = .;
        *(.bss*)
        *(COMMON)
        _bss_end = .;
    }

    _kernel_end = .;

    /DISCARD/ : {
        *(.note*)
        *(.eh_frame*)
        *(.comment)
    }
}
