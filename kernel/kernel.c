#include "shell.h"
#include "vga.h"

/* YoroOS kernel entry point (called from entry.S). */
void kernel_main(void) {
    vga_init();
    print_banner();
    shell_run(); /* never returns */
}
