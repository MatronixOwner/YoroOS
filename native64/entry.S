/* A private stack; no firmware calls or firmware interrupt handlers afterwards. */
    .section .text
    .globl yoro_enter_kernel
    .type yoro_enter_kernel,@function
yoro_enter_kernel:
    cli
    leaq yoro_stack_top(%rip), %rsp
    andq $-16, %rsp
    cld
    call yoro_kernel_main
1:  hlt
    jmp 1b
    .section .bss
    .balign 16
yoro_stack:
    .skip 32768
yoro_stack_top:
    .section .note.GNU-stack,"",@progbits
/* PE/COFF base relocation block: image is position independent. */
    .section .reloc,"a",@progbits
    .long 0
    .long 12
    .short 0
    .short 0
