#include "yorofs.h"

struct entry { char name[YFS_NAME_MAX + 1]; char data[YFS_DATA_MAX + 1]; int used; };
static struct entry files[YFS_MAX_FILES];
static size_t len(const char *s) { size_t i = 0; while (s[i]) ++i; return i; }
static int eq(const char *a, const char *b) { while (*a && *a == *b) { ++a; ++b; } return *a == *b; }
static void copy(char *a, const char *b) { while ((*a++ = *b++)) {} }
static int valid(const char *s) {
    size_t n = len(s);
    if (!n || n > YFS_NAME_MAX || eq(s, ".") || eq(s, "..")) return 0;
    while (*s) {
        char c = *s++;
        if (!((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') ||
              (c >= '0' && c <= '9') || c == '.' || c == '_' || c == '-')) return 0;
    }
    return 1;
}
static int find(const char *name) {
    for (int i = 0; i < YFS_MAX_FILES; ++i)
        if (files[i].used && eq(files[i].name, name)) return i;
    return -1;
}
void yfs_init(void) { for (int i = 0; i < YFS_MAX_FILES; ++i) files[i].used = 0; }
enum yfs_result yfs_write(const char *name, const char *data) {
    if (!valid(name)) return YFS_INVALID;
    if (len(data) > YFS_DATA_MAX) return YFS_TOO_LARGE;
    int i = find(name);
    if (i < 0) {
        for (i = 0; i < YFS_MAX_FILES && files[i].used; ++i) {}
        if (i == YFS_MAX_FILES) return YFS_FULL;
    }
    copy(files[i].name, name); copy(files[i].data, data); files[i].used = 1;
    return YFS_OK;
}
enum yfs_result yfs_remove(const char *name) {
    if (!valid(name)) return YFS_INVALID;
    int i = find(name);
    if (i < 0) return YFS_NOT_FOUND;
    files[i].used = 0;
    return YFS_OK;
}
const char *yfs_read(const char *name) {
    int i = find(name); return i < 0 ? 0 : files[i].data;
}
const char *yfs_name_at(size_t i) {
    return i < YFS_MAX_FILES && files[i].used ? files[i].name : 0;
}
int yfs_command(const char *cmd, const char *arg, void (*out)(const char *)) {
    if (eq(cmd, "ls")) {
        if (*arg) { out("Usage: ls\n"); return 1; }
        int count = 0;
        for (size_t i = 0; i < YFS_MAX_FILES; ++i) {
            const char *name = yfs_name_at(i);
            if (name) { out(name); out("\n"); ++count; }
        }
        if (!count) out("(empty)\n");
        return 1;
    }
    if (eq(cmd, "fsinfo")) {
        out("YoroFS prototype: RAM only; files vanish on reboot. 16 files, 511 bytes each.\n");
        return 1;
    }
    int writing = eq(cmd, "write"), reading = eq(cmd, "cat"), removing = eq(cmd, "rm");
    if (!writing && !reading && !removing) return 0;
    char name[YFS_NAME_MAX + 1]; size_t n = 0;
    while (arg[n] && arg[n] != ' ' && arg[n] != '\t') {
        if (n == YFS_NAME_MAX) { out("Invalid name (max 31 characters).\n"); return 1; }
        name[n] = arg[n]; ++n;
    }
    name[n] = 0;
    const char *rest = arg + n;
    while (*rest == ' ' || *rest == '\t') ++rest;
    if (!valid(name) || (!writing && *rest)) {
        out("Usage: write <name> <text> | cat <name> | rm <name>\n"); return 1;
    }
    if (reading) {
        const char *data = yfs_read(name);
        if (!data) out("File not found.\n");
        else { out(data); out("\n"); }
    } else {
        enum yfs_result r = writing ? yfs_write(name, rest) : yfs_remove(name);
        if (r == YFS_OK) out(writing ? "Written to RAM (not saved to disk).\n" : "Deleted.\n");
        else if (r == YFS_FULL) out("YoroFS is full.\n");
        else if (r == YFS_TOO_LARGE) out("File too large.\n");
        else if (r == YFS_NOT_FOUND) out("File not found.\n");
        else out("Invalid name.\n");
    }
    return 1;
}
