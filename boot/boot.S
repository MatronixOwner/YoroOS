/*
 * YoroOS BIOS boot loader.
 *
 * Loaded by the BIOS from CD (El Torito, no-emulation) at 0000:7C00.
 * Reads the kernel image from the CD using INT 13h extensions into
 * physical memory at 0x10000, switches to 32-bit protected mode and
 * jumps to the kernel entry point.
 *
 * kernel_lba / kernel_sectors below are patched by tools/mkiso.py
 * when the ISO image is built (magic values 0xDEADBEEF / 0xCAFEBABE).
 */

    .code16
    .text
    .globl _start

_start:
    ljmp $0x0000, $start            /* normalize CS:IP -> 0000:7Cxx */

start:
    cli
    xorw %ax, %ax
    movw %ax, %ds
    movw %ax, %es
    movw %ax, %ss
    movw $0x7C00, %sp               /* stack just below the boot sector */
    sti
    cld
    movb %dl, boot_drive            /* BIOS boot drive (CD) */

    /* Set 80x25 text mode (also clears the screen). */
    movw $0x0003, %ax
    int $0x10

    movw $msg_loading, %si
    call print

    /* Check INT 13h extensions (needed for CD LBA reads). */
    movb $0x41, %ah
    movw $0x55AA, %bx
    movb boot_drive, %dl
    int $0x13
    jc no_extensions
    cmpw $0xAA55, %bx
    jne no_extensions

    /* Prepare the disk address packet with the patched kernel location. */
    movl kernel_lba, %eax
    movl %eax, dap_lba
    movl kernel_sectors, %eax
    movl %eax, sectors_left

load_loop:
    cmpl $0, sectors_left
    je load_done

    movw $dap, %si
    movb $0x42, %ah                 /* extended read */
    movb boot_drive, %dl
    int $0x13
    jc disk_error

    addw $0x80, dap_seg             /* next buffer: +2048 bytes */
    incl dap_lba
    decl sectors_left

    movb $'.', %al                  /* progress dot */
    movb $0x0E, %ah
    int $0x10
    jmp load_loop

load_done:
    movw $msg_ok, %si
    call print

    /* Enable the A20 line (BIOS call, then the fast port 0x92 way). */
    movw $0x2401, %ax
    int $0x15
    inb $0x92, %al
    orb $0x02, %al
    andb $0xFE, %al
    outb %al, $0x92

    /* Switch to 32-bit protected mode. */
    cli
    lgdt gdt_desc
    movl %cr0, %eax
    orl $1, %eax                    /* CR0.PE */
    movl %eax, %cr0
    ljmpl $0x08, $pm_start          /* flush prefetch, load CS */

    .code32
pm_start:
    movw $0x10, %ax                 /* flat data segment */
    movw %ax, %ds
    movw %ax, %es
    movw %ax, %fs
    movw %ax, %gs
    movw %ax, %ss
    movl $0x9FC00, %esp             /* temp stack; kernel sets its own */
    movl $0x10000, %eax             /* kernel entry */
    jmp *%eax

    .code16

no_extensions:
    movw $msg_noext, %si
    call print
    jmp wait_reboot

disk_error:
    movw $msg_diskerr, %si
    call print
    jmp wait_reboot

wait_reboot:
    xorb %ah, %ah                   /* wait for a key */
    int $0x16
    int $0x19                       /* reboot */
1:  hlt
    jmp 1b

/* print: DS:SI -> zero-terminated string (BIOS teletype) */
print:
    lodsb
    testb %al, %al
    jz 1f
    movb $0x0E, %ah
    movw $0x0007, %bx
    int $0x10
    jmp print
1:  ret

/* ---- data ---- */

boot_drive:     .byte 0

msg_loading:    .asciz "YoroOS Loader v0.2\r\nLoading kernel"
msg_ok:         .asciz " OK\r\nStarting YoroOS...\r\n"
msg_noext:      .asciz "\r\nERROR: INT 13h extensions not supported.\r\nPress any key to reboot..."
msg_diskerr:    .asciz "\r\nERROR: failed to read kernel from CD.\r\nPress any key to reboot..."

/* Disk Address Packet for INT 13h AH=42h (one 2048-byte CD sector). */
    .balign 2
dap:
    .byte 0x10                      /* packet size */
    .byte 0                         /* reserved */
    .word 1                         /* sectors to read */
    .word 0x0000                    /* buffer offset */
dap_seg:
    .word 0x1000                    /* buffer segment -> phys 0x10000 */
dap_lba:
    .long 0                         /* LBA low (filled at runtime) */
    .long 0                         /* LBA high */

sectors_left:   .long 0

/* Flat GDT: null, 32-bit code, 32-bit data (base 0, limit 4 GiB). */
    .balign 8
gdt_start:
    .quad 0x0000000000000000
    .quad 0x00CF9A000000FFFF        /* code 0x08 */
    .quad 0x00CF92000000FFFF        /* data 0x10 */
gdt_end:
gdt_desc:
    .word gdt_end - gdt_start - 1
    .long gdt_start

/* Patched by tools/mkiso.py: kernel location inside the ISO. */
    .balign 4
kernel_lba:     .long 0xDEADBEEF
kernel_sectors: .long 0xCAFEBABE

    .org 510
    .word 0xAA55                    /* boot signature */
