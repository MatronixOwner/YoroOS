/*
 * YoroOS kernel entry point.
 * Control arrives here (physical 0x10000) in 32-bit protected mode
 * with flat segments already set up by the boot loader.
 */

    .section .text.entry
    .globl _start
_start:
    movw $0x10, %ax
    movw %ax, %ds
    movw %ax, %es
    movw %ax, %fs
    movw %ax, %gs
    movw %ax, %ss
    movl $stack_top, %esp

    /* Zero the BSS. */
    movl $_bss_start, %edi
    movl $_bss_end, %ecx
    subl %edi, %ecx
    xorb %al, %al
    rep stosb

    call kernel_main

hang:
    cli
    hlt
    jmp hang

    .section .bss
    .balign 16
stack_bottom:
    .skip 16384                     /* 16 KiB kernel stack */
stack_top:
