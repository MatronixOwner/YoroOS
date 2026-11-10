#include "yorofs.h"
#include "shell.h"
#include "cpu.h"
#include "io.h"
#include "keyboard.h"
#include "rtc.h"
#include "string.h"
#include "types.h"
#include "vga.h"

#define YOROOS_VERSION "0.3.0-dev1"

#define LINE_MAX 128
#define HISTORY_MAX 16

static char history[HISTORY_MAX][LINE_MAX];
static int history_count = 0;

void print_banner(void) {
    uint8_t saved_fg = vga_get_fg();
    vga_setcolor(VGA_LIGHT_CYAN, VGA_BLACK);
    vga_puts("  __   __               ___  ____\n");
    vga_puts("  \\ \\ / /__  _ __ ___  / _ \\/ ___|\n");
    vga_puts("   \\ V / _ \\| '__/ _ \\| | | \\___ \\\n");
    vga_puts("    | | (_) | | | (_) | |_| |___) |\n");
    vga_puts("    |_|\\___/|_|  \\___/ \\___/|____/\n");
    vga_setcolor(VGA_LIGHT_GREY, VGA_BLACK);
    vga_printf("  YoroOS version %s (x86, custom kernel)\n", YOROOS_VERSION);
    vga_printf("  Built: %s %s\n\n", __DATE__, __TIME__);
    vga_setcolor(saved_fg, VGA_BLACK);
}

/* ---------------- command implementations ---------------- */

static void cmd_help(void) {
    vga_puts("Available commands:\n");
    vga_puts("  help            show this help\n");
    vga_puts("  clear           clear the screen (or Ctrl+L)\n");
    vga_puts("  echo <text>     print text\n");
    vga_puts("  about           about YoroOS\n");
    vga_puts("  version         show YoroOS version\n");
    vga_puts("  banner          show the YoroOS logo again\n");
    vga_puts("  cpu             processor information\n");
    vga_puts("  mem             memory size\n");
    vga_puts("  date            current date and time (RTC)\n");
    vga_puts("  color <0-15>    change text color\n");
    vga_puts("  ls / write / cat / rm / fsinfo  RAM files (not persistent)\n");
    vga_puts("  reboot          restart the machine\n");
    vga_puts("  shutdown        power off\n");
    vga_puts("\nKeys: Up/Down = history, Ctrl+C = cancel line, Ctrl+L = clear\n");
}

static void cmd_about(void) {
    vga_puts("YoroOS is a small hobby operating system written from scratch.\n");
    vga_puts("Custom BIOS boot loader + 32-bit kernel in C.\n");
    vga_printf("Version: %s\n", YOROOS_VERSION);
}

static void cmd_cpu(void) {
    char vendor[13];
    char brand[49];
    cpu_get_vendor(vendor);
    cpu_get_brand(brand);

    /* Trim leading spaces of the brand string. */
    char *b = brand;
    while (*b == ' ')
        b++;

    vga_printf("CPU vendor: %s\n", vendor);
    vga_printf("CPU model : %s\n", b);
}

static void cmd_mem(void) {
    uint32_t kb = cmos_total_memory_kb();
    vga_printf("Memory: %u KiB (%u MiB)\n", kb, kb / 1024);
}

static void cmd_date(void) {
    struct rtc_time t;
    rtc_read(&t);
    vga_printf("%02d.%02d.%04d %02d:%02d:%02d\n", t.day, t.month, t.year,
               t.hour, t.minute, t.second);
}

static const char *color_names[16] = {
    "black", "blue", "green", "cyan", "red", "magenta", "коричневые",
    "light-grey", "dark-grey", "light-blue", "light-green", "light-cyan",
    "light-red", "pink", "yellow", "white",
};

static void cmd_color(const char *arg) {
    if (*arg == '\0') {
        vga_puts("Usage: color <0-15>\n");
        vga_puts(" 0 black    4 red        8 dark-grey   12 light-red\n");
        vga_puts(" 1 blue     5 magenta    9 light-blue  13 pink\n");
        vga_puts(" 2 green    6 коричневые     10 light-green 14 yellow\n");
        vga_puts(" 3 cyan     7 light-grey 11 light-cyan 15 white\n");
        return;
    }
    int n = atoi(arg);
    if (n < 0 || n > 15) {
        vga_puts("Color must be between 0 and 15.\n");
        return;
    }
    if (n == VGA_BLACK) {
        vga_puts("Black on black would be invisible :)\n");
        return;
    }
    vga_setcolor((uint8_t)n, VGA_BLACK);
    vga_printf("Text color: %s\n", color_names[n]);
}

static void cmd_reboot(void) {
    vga_puts("Rebooting...\n");
    while (inb(0x64) & 0x02)
        ;                    /* wait until the controller is ready */
    outb(0x64, 0xFE);        /* pulse the CPU reset line */
    for (;;)
        __asm__ volatile("hlt");
}

static void cmd_shutdown(void) {
    vga_puts("Shutting down...\n");
    outw(0x604, 0x2000);     /* QEMU (new) */
    outw(0xB004, 0x2000);    /* Bochs / old QEMU */
    outw(0x4004, 0x3400);    /* VirtualBox */
    vga_puts("It is now safe to turn off the computer.\n");
    __asm__ volatile("cli");
    for (;;)
        __asm__ volatile("hlt");
}

/* ---------------- line input with history ---------------- */

static const char prompt[] = "yoro@YoroOS:~$ ";

static void erase_chars(size_t n) {
    for (size_t i = 0; i < n; i++)
        vga_putchar('\b');
}

/*
 * Read one line into buf. Returns false if cancelled with Ctrl+C.
 */
static bool readline(char *buf, size_t size) {
    size_t len = 0;
    int hist_pos = history_count;
    buf[0] = '\0';

    for (;;) {
        int key = keyboard_readkey();

        if (key == '\n') {
            vga_putchar('\n');
            buf[len] = '\0';
            return true;
        }
        if (key == '\b') {
            if (len > 0) {
                len--;
                buf[len] = '\0';
                vga_putchar('\b');
            }
            continue;
        }
        if (key == 3) { /* Ctrl+C */
            vga_puts("^C\n");
            buf[0] = '\0';
            return false;
        }
        if (key == 12) { /* Ctrl+L */
            vga_clear();
            vga_puts(prompt);
            buf[len] = '\0';
            vga_puts(buf);
            continue;
        }
        if (key == KEY_UP || key == KEY_DOWN) {
            if (history_count == 0)
                continue;
            if (key == KEY_UP && hist_pos > 0)
                hist_pos--;
            if (key == KEY_DOWN && hist_pos < history_count)
                hist_pos++;
            erase_chars(len);
            if (hist_pos < history_count) {
                strcpy(buf, history[hist_pos]);
            } else {
                buf[0] = '\0';
            }
            len = strlen(buf);
            vga_puts(buf);
            continue;
        }
        if (key >= 32 && key < 127 && len < size - 1) {
            buf[len++] = (char)key;
            buf[len] = '\0';
            vga_putchar((char)key);
        }
    }
}

static void history_add(const char *line) {
    if (line[0] == '\0')
        return;
    if (history_count > 0 && strcmp(history[history_count - 1], line) == 0)
        return;
    if (history_count == HISTORY_MAX) {
        for (int i = 1; i < HISTORY_MAX; i++)
            strcpy(history[i - 1], history[i]);
        history_count--;
    }
    strcpy(history[history_count++], line);
}

/* ---------------- command dispatch ---------------- */

static void execute(char *line) {
    /* Skip leading spaces. */
    while (*line == ' ' || *line == '\t')
        line++;
    if (*line == '\0')
        return;

    /* Split command and arguments. */
    char *arg = line;
    while (*arg && *arg != ' ' && *arg != '\t')
        arg++;
    if (*arg) {
        *arg++ = '\0';
        while (*arg == ' ' || *arg == '\t')
            arg++;
    }

    if (yfs_command(line, arg, vga_puts)) return;

    if (strcmp(line, "help") == 0) {
        cmd_help();
    } else if (strcmp(line, "clear") == 0) {
        vga_clear();
    } else if (strcmp(line, "echo") == 0) {
        vga_puts(arg);
        vga_putchar('\n');
    } else if (strcmp(line, "about") == 0 || strcmp(line, "info") == 0) {
        cmd_about();
    } else if (strcmp(line, "version") == 0 || strcmp(line, "ver") == 0) {
        vga_printf("YoroOS %s\n", YOROOS_VERSION);
    } else if (strcmp(line, "banner") == 0 || strcmp(line, "logo") == 0) {
        print_banner();
    } else if (strcmp(line, "cpu") == 0) {
        cmd_cpu();
    } else if (strcmp(line, "mem") == 0) {
        cmd_mem();
    } else if (strcmp(line, "date") == 0 || strcmp(line, "time") == 0) {
        cmd_date();
    } else if (strcmp(line, "color") == 0) {
        cmd_color(arg);
    } else if (strcmp(line, "reboot") == 0) {
        cmd_reboot();
    } else if (strcmp(line, "shutdown") == 0 ||
               strcmp(line, "poweroff") == 0 || strcmp(line, "halt") == 0) {
        cmd_shutdown();
    } else {
        vga_printf("Unknown command: %s\nType 'help' to list commands.\n",
                   line);
    }
}

void shell_run(void) {
    yfs_init();
    static char line[LINE_MAX];
    vga_puts("Type 'help' to see available commands.\n\n");

    for (;;) {
        vga_setcolor(VGA_LIGHT_GREEN, VGA_BLACK);
        vga_puts("yoro@YoroOS");
        vga_setcolor(VGA_LIGHT_GREY, VGA_BLACK);
        vga_puts(":~$ ");

        if (readline(line, sizeof(line))) {
            history_add(line);
            execute(line);
        }
    }
}
