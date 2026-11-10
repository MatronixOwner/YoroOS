#include "yorofs.h"
/*
 * YoroOS UEFI application (BOOTX64.EFI).
 *
 * Hyper-V Generation 2 / UEFI machines have no VGA text mode and no
 * PS/2 keyboard, so on UEFI YoroOS runs on the firmware console
 * (Simple Text Output/Input) and never calls ExitBootServices.
 * The command set mirrors the BIOS kernel shell.
 */

#include "efi.h"

#include <stdarg.h>

#define YOROOS_VERSION "0.3.0-dev1"

static struct EFI_SYSTEM_TABLE *ST;
static UINTN text_fg = EFI_LIGHTGRAY;

#define LINE_MAX 128
#define HISTORY_MAX 16
static char history[HISTORY_MAX][LINE_MAX];
static int history_count = 0;

/* ---------- tiny helpers (no libc) ---------- */

static size_t kstrlen(const char *s) {
    size_t n = 0;
    while (s[n])
        n++;
    return n;
}

static int kstrcmp(const char *a, const char *b) {
    while (*a && *a == *b) {
        a++;
        b++;
    }
    return (int)(uint8_t)*a - (int)(uint8_t)*b;
}

static void kstrcpy(char *d, const char *s) {
    while ((*d++ = *s++))
        ;
}

static int katoi(const char *s) {
    int v = 0;
    while (*s == ' ')
        s++;
    while (*s >= '0' && *s <= '9')
        v = v * 10 + (*s++ - '0');
    return v;
}

static char *kutoa(uint64_t value, char *buf, int base) {
    char tmp[32];
    int i = 0;
    if (value == 0) {
        buf[0] = '0';
        buf[1] = 0;
        return buf;
    }
    while (value) {
        uint64_t d = value % (uint64_t)base;
        tmp[i++] = (char)(d < 10 ? '0' + d : 'a' + d - 10);
        value /= (uint64_t)base;
    }
    int j = 0;
    while (i > 0)
        buf[j++] = tmp[--i];
    buf[j] = 0;
    return buf;
}

/* ---------- console output ---------- */

static void print_w(const char *s) {
    CHAR16 buf[256];
    size_t n = 0;
    EFI_TEXT_OUTPUT_STRING out =
        (EFI_TEXT_OUTPUT_STRING)ST->ConOut->OutputString;
    for (const char *p = s; *p; p++) {
        if (*p == '\n') {
            buf[n++] = '\r';
        }
        buf[n++] = (CHAR16)(uint8_t)*p;
        if (n > 250) {
            buf[n] = 0;
            out(ST->ConOut, buf);
            n = 0;
        }
    }
    if (n) {
        buf[n] = 0;
        out(ST->ConOut, buf);
    }
}

static void putchar_a(char c) {
    char s[2] = {c, 0};
    print_w(s);
}

static void printf_a(const char *fmt, ...) {
    va_list ap;
    va_start(ap, fmt);
    char num[32];
    for (const char *p = fmt; *p; p++) {
        if (*p != '%') {
            putchar_a(*p);
            continue;
        }
        p++;
        int zero_pad = 0;
        if (*p == '0' && p[1] >= '0' && p[1] <= '9') {
            zero_pad = p[1] - '0';
            p += 2;
        }
        bool lng = false;
        if (*p == 'l' || *p == 'z') {
            lng = true;
            p++;
            if (*p == 'l')
                p++;
        }
        switch (*p) {
        case 's': {
            const char *s = va_arg(ap, const char *);
            print_w(s ? s : "(null)");
            break;
        }
        case 'c':
            putchar_a((char)va_arg(ap, int));
            break;
        case 'd':
        case 'i': {
            long v = lng ? va_arg(ap, long) : va_arg(ap, int);
            if (v < 0) {
                putchar_a('-');
                v = -v;
                zero_pad--;
            }
            kutoa((uint64_t)v, num, 10);
            size_t len = kstrlen(num);
            while ((int)len < zero_pad) {
                putchar_a('0');
                len++;
            }
            print_w(num);
            break;
        }
        case 'u':
            kutoa(lng ? va_arg(ap, uint64_t)
                      : (uint64_t)va_arg(ap, unsigned int),
                  num, 10);
            print_w(num);
            break;
        case 'x':
        case 'X':
            kutoa(lng ? va_arg(ap, uint64_t)
                      : (uint64_t)va_arg(ap, unsigned int),
                  num, 16);
            print_w(num);
            break;
        case '%':
            putchar_a('%');
            break;
        default:
            putchar_a('%');
            if (*p)
                putchar_a(*p);
            break;
        }
    }
    va_end(ap);
}

static void set_color(UINTN fg) {
    text_fg = fg;
    EFI_TEXT_SET_ATTRIBUTE sa =
        (EFI_TEXT_SET_ATTRIBUTE)ST->ConOut->SetAttribute;
    sa(ST->ConOut, fg | (EFI_BLACK << 4));
}

static void clear_screen(void) {
    EFI_TEXT_CLEAR_SCREEN cs = (EFI_TEXT_CLEAR_SCREEN)ST->ConOut->ClearScreen;
    cs(ST->ConOut);
}

static void print_banner(void) {
    UINTN saved = text_fg;
    set_color(EFI_LIGHTCYAN);
    print_w("  __   __               ___  ____\n");
    print_w("  \\ \\ / /__  _ __ ___  / _ \\/ ___|\n");
    print_w("   \\ V / _ \\| '__/ _ \\| | | \\___ \\\n");
    print_w("    | | (_) | | | (_) | |_| |___) |\n");
    print_w("    |_|\\___/|_|  \\___/ \\___/|____/\n");
    set_color(EFI_LIGHTGRAY);
    printf_a("  YoroOS version %s (UEFI x86-64)\n", YOROOS_VERSION);
    printf_a("  Firmware: ");
    /* FirmwareVendor is already CHAR16 text. */
    ((EFI_TEXT_OUTPUT_STRING)ST->ConOut->OutputString)(ST->ConOut,
                                                       ST->FirmwareVendor);
    printf_a("  Built: %s %s\n\n", __DATE__, __TIME__);
    set_color(saved);
}

/* ---------- keyboard input ---------- */

static struct EFI_INPUT_KEY read_key(void) {
    struct EFI_INPUT_KEY key;
    EFI_WAIT_FOR_EVENT wait_ev =
        (EFI_WAIT_FOR_EVENT)ST->BootServices->WaitForEvent;
    EFI_INPUT_READ_KEY readk =
        (EFI_INPUT_READ_KEY)ST->ConIn->ReadKeyStroke;
    for (;;) {
        UINTN index = 0;
        key.ScanCode = 0;
        key.UnicodeChar = 0;
        if (readk(ST->ConIn, &key) == EFI_SUCCESS)
            return key;
        wait_ev(1, &ST->ConIn->WaitForKey, &index);
    }
}

/* ---------- commands ---------- */

static void cpuid(uint32_t leaf, uint32_t regs[4]) {
    __asm__ volatile("cpuid"
                     : "=a"(regs[0]), "=b"(regs[1]), "=c"(regs[2]),
                       "=d"(regs[3])
                     : "a"(leaf));
}

static void cmd_cpu(void) {
    uint32_t r[4];
    char vendor[13];
    cpuid(0, r);
    *(uint32_t *)(vendor + 0) = r[1];
    *(uint32_t *)(vendor + 4) = r[3];
    *(uint32_t *)(vendor + 8) = r[2];
    vendor[12] = 0;
    printf_a("CPU vendor: %s\n", vendor);

    cpuid(0x80000000u, r);
    if (r[0] >= 0x80000004u) {
        char brand[49];
        uint32_t *p = (uint32_t *)brand;
        for (int i = 0; i < 3; i++) {
            cpuid(0x80000002u + (uint32_t)i, r);
            p[i * 4 + 0] = r[0];
            p[i * 4 + 1] = r[1];
            p[i * 4 + 2] = r[2];
            p[i * 4 + 3] = r[3];
        }
        brand[48] = 0;
        char *b = brand;
        while (*b == ' ')
            b++;
        printf_a("CPU model : %s\n", b);
    }
}

static void cmd_mem(void) {
    static uint8_t buffer[16384];
    UINTN size = sizeof(buffer), key = 0, desc_size = 0;
    uint32_t desc_ver = 0;
    EFI_GET_MEMORY_MAP get_map =
        (EFI_GET_MEMORY_MAP)ST->BootServices->GetMemoryMap;
    EFI_STATUS st = get_map(&size, (struct EFI_MEMORY_DESCRIPTOR *)buffer,
                            &key, &desc_size, &desc_ver);
    if (st != EFI_SUCCESS || desc_size == 0) {
        print_w("Could not read the memory map.\n");
        return;
    }
    uint64_t total = 0;
    for (UINTN off = 0; off + sizeof(struct EFI_MEMORY_DESCRIPTOR) <= size;
         off += desc_size) {
        struct EFI_MEMORY_DESCRIPTOR *d =
            (struct EFI_MEMORY_DESCRIPTOR *)(buffer + off);
        /* RAM-ish types: loader/boot/runtime data+code and free memory. */
        if (d->Type >= 1 && d->Type <= 7)
            total += d->NumberOfPages * 4096;
    }
    printf_a("Memory: %lu KiB (%lu MiB)\n",
             (unsigned long)(total / 1024),
             (unsigned long)(total / 1024 / 1024));
}

static void cmd_date(void) {
    struct EFI_TIME t;
    EFI_GET_TIME get_time = (EFI_GET_TIME)ST->RuntimeServices->GetTime;
    if (get_time(&t, NULL) == EFI_SUCCESS)
        printf_a("%02d.%02d.%04d %02d:%02d:%02d\n", t.Day, t.Month, t.Year,
                 t.Hour, t.Minute, t.Second);
    else
        print_w("Could not read the clock.\n");
}

static const char color_names[16][16] = {
    "black",       "blue",    "green",   "cyan",    "red",
    "magenta",     "brown",   "light-grey", "dark-grey", "light-blue",
    "light-green", "light-cyan", "light-red", "pink",    "yellow",
    "white",
};

static void cmd_color(const char *arg) {
    if (*arg == 0) {
        print_w("Usage: color <0-15>   (7 grey, 10 light-green, 14 yellow,"
                " 15 white)\n");
        return;
    }
    int n = katoi(arg);
    if (n < 1 || n > 15) {
        print_w("Color must be between 1 and 15.\n");
        return;
    }
    set_color((UINTN)n);
    printf_a("Text color: %s\n", color_names[n]);
}

static void cmd_reset(int type, const char *msg) {
    print_w(msg);
    EFI_RESET_SYSTEM reset = (EFI_RESET_SYSTEM)ST->RuntimeServices->ResetSystem;
    reset(type, EFI_SUCCESS, 0, NULL);
    for (;;)
        __asm__ volatile("hlt");
}

static bool execute(char *line) {
    while (*line == ' ' || *line == '\t')
        line++;
    if (*line == 0)
        return true;
    char *arg = line;
    while (*arg && *arg != ' ' && *arg != '\t')
        arg++;
    if (*arg) {
        *arg++ = 0;
        while (*arg == ' ' || *arg == '\t')
            arg++;
    }

    if (yfs_command(line, arg, print_w)) return true;

    if (kstrcmp(line, "help") == 0) {
        print_w("Available commands:\n");
        print_w("  help            show this help\n");
        print_w("  clear           clear the screen (or Ctrl+L)\n");
        print_w("  echo <text>     print text\n");
        print_w("  about           about YoroOS\n");
        print_w("  version         show YoroOS version\n");
        print_w("  banner          show the YoroOS logo again\n");
        print_w("  cpu             processor information\n");
        print_w("  mem             memory size\n");
        print_w("  date            current date and time\n");
        print_w("  color <0-15>    change text color\n");
        print_w("  ls / write / cat / rm / fsinfo  RAM files (not persistent)\n");
        print_w("  reboot          restart the machine\n");
        print_w("  shutdown        power off\n");
        print_w("  exit            exit to the firmware boot menu\n");
        print_w("\nKeys: Up/Down = history, Ctrl+C = cancel line,"
                " Ctrl+L = clear\n");
    } else if (kstrcmp(line, "clear") == 0) {
        clear_screen();
    } else if (kstrcmp(line, "echo") == 0) {
        print_w(arg);
        print_w("\n");
    } else if (kstrcmp(line, "about") == 0 || kstrcmp(line, "info") == 0) {
        print_w("YoroOS is a small hobby operating system written from"
                " scratch.\n");
        print_w("You are running the UEFI edition: the shell lives on the"
                " firmware console.\n");
        printf_a("Version: %s\n", YOROOS_VERSION);
    } else if (kstrcmp(line, "version") == 0 || kstrcmp(line, "ver") == 0) {
        printf_a("YoroOS %s\n", YOROOS_VERSION);
    } else if (kstrcmp(line, "banner") == 0 || kstrcmp(line, "logo") == 0) {
        print_banner();
    } else if (kstrcmp(line, "cpu") == 0) {
        cmd_cpu();
    } else if (kstrcmp(line, "mem") == 0) {
        cmd_mem();
    } else if (kstrcmp(line, "date") == 0 || kstrcmp(line, "time") == 0) {
        cmd_date();
    } else if (kstrcmp(line, "color") == 0) {
        cmd_color(arg);
    } else if (kstrcmp(line, "reboot") == 0) {
        cmd_reset(EFI_RESET_WARM, "Rebooting...\n");
    } else if (kstrcmp(line, "shutdown") == 0 ||
               kstrcmp(line, "poweroff") == 0 || kstrcmp(line, "halt") == 0) {
        cmd_reset(EFI_RESET_SHUTDOWN, "Shutting down...\n");
    } else if (kstrcmp(line, "exit") == 0 || kstrcmp(line, "quit") == 0) {
        print_w("Bye! Returning to the firmware...\n");
        return false;
    } else {
        printf_a("Unknown command: %s\nType 'help' to list commands.\n", line);
    }
    return true;
}

/* ---------- line input ---------- */

static void erase_chars(size_t n) {
    while (n--)
        print_w("\b \b");
}

static bool readline(char *buf, size_t size, bool *cancelled) {
    size_t len = 0;
    int hist_pos = history_count;
    *cancelled = false;
    buf[0] = 0;

    for (;;) {
        struct EFI_INPUT_KEY key = read_key();
        if (key.ScanCode == 0x01 || key.ScanCode == 0x02) { /* Up/Down */
            if (history_count == 0)
                continue;
            if (key.ScanCode == 0x01 && hist_pos > 0)
                hist_pos--;
            if (key.ScanCode == 0x02 && hist_pos < history_count)
                hist_pos++;
            erase_chars(len);
            if (hist_pos < history_count)
                kstrcpy(buf, history[hist_pos]);
            else
                buf[0] = 0;
            len = kstrlen(buf);
            print_w(buf);
            continue;
        }

        CHAR16 ch = key.UnicodeChar;
        if (ch == '\r' || ch == '\n') {
            print_w("\n");
            buf[len] = 0;
            return true;
        }
        if (ch == 0x0008) { /* Backspace */
            if (len > 0) {
                len--;
                buf[len] = 0;
                print_w("\b \b");
            }
            continue;
        }
        if (ch == 0x0003) { /* Ctrl+C */
            print_w("^C\n");
            *cancelled = true;
            buf[0] = 0;
            return true;
        }
        if (ch == 0x000C) { /* Ctrl+L */
            clear_screen();
            set_color(EFI_LIGHTGREEN);
            print_w("yoro@YoroOS");
            set_color(text_fg == EFI_LIGHTGREEN ? EFI_LIGHTGRAY : text_fg);
            print_w(":~$ ");
            print_w(buf);
            continue;
        }
        if (ch >= 0x20 && ch < 0x7F && len < size - 1) {
            buf[len++] = (char)ch;
            buf[len] = 0;
            putchar_a((char)ch);
        }
    }
}

static void history_add(const char *line) {
    if (line[0] == 0)
        return;
    if (history_count > 0 && kstrcmp(history[history_count - 1], line) == 0)
        return;
    if (history_count == HISTORY_MAX) {
        for (int i = 1; i < HISTORY_MAX; i++)
            kstrcpy(history[i - 1], history[i]);
        history_count--;
    }
    kstrcpy(history[history_count++], line);
}

/* ---------- entry point ---------- */

EFI_STATUS EFIAPI efi_main(EFI_HANDLE ImageHandle,
                           struct EFI_SYSTEM_TABLE *SystemTable) {
    (void)ImageHandle;
    ST = SystemTable;
    yfs_init();

    /* Do not let the firmware reboot us after 5 minutes of idling. */
    EFI_SET_WATCHDOG_TIMER wdt =
        (EFI_SET_WATCHDOG_TIMER)ST->BootServices->SetWatchdogTimer;
    wdt(0, 0, 0, NULL);

    set_color(EFI_LIGHTGRAY);
    clear_screen();
    print_banner();
    print_w("Type 'help' to see available commands. "
            "Type 'exit' to return to firmware.\n\n");

    static char line[LINE_MAX];
    for (;;) {
        UINTN user_fg = text_fg;
        set_color(EFI_LIGHTGREEN);
        print_w("yoro@YoroOS");
        set_color(user_fg == EFI_LIGHTGREEN ? EFI_LIGHTGRAY : user_fg);
        print_w(":~$ ");

        bool cancelled = false;
        readline(line, sizeof(line), &cancelled);
        if (cancelled)
            continue;
        history_add(line);
        if (!execute(line))
            break;
    }
    return EFI_SUCCESS;
}
