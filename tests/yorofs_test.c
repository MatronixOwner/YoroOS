#include "yorofs.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static char output[8192];
static void capture(const char *s) { assert(strlen(output) + strlen(s) < sizeof(output)); strcat(output, s); }
static void cmd(const char *name, const char *arg, const char *expected) {
    output[0] = 0; assert(yfs_command(name, arg, capture)); assert(strstr(output, expected));
}
int main(void) {
    char name[40], data[YFS_DATA_MAX + 2];
    yfs_init(); cmd("ls", "", "(empty)");
    cmd("write", "hello.txt hello YoroOS", "Written");
    cmd("cat", "hello.txt", "hello YoroOS");
    cmd("ls", "", "hello.txt");
    cmd("write", "hello.txt replacement", "Written");
    assert(strcmp(yfs_read("hello.txt"), "replacement") == 0);
    assert(yfs_write("../bad", "x") == YFS_INVALID);
    assert(yfs_write("", "x") == YFS_INVALID);
    memset(data, 'x', YFS_DATA_MAX + 1); data[YFS_DATA_MAX + 1] = 0;
    assert(yfs_write("hello.txt", data) == YFS_TOO_LARGE);
    assert(strcmp(yfs_read("hello.txt"), "replacement") == 0);
    data[YFS_DATA_MAX] = 0; assert(yfs_write("hello.txt", data) == YFS_OK);
    for (int i = 0; i < YFS_MAX_FILES - 1; ++i) { snprintf(name, sizeof name, "f%d", i); assert(yfs_write(name, "") == YFS_OK); }
    assert(yfs_write("overflow", "x") == YFS_FULL);
    assert(yfs_write("hello.txt", "still writable") == YFS_OK);
    cmd("rm", "hello.txt", "Deleted"); cmd("cat", "hello.txt", "not found");
    assert(yfs_write("overflow", "x") == YFS_OK);
    cmd("cat", "overflow extra", "Usage");
    cmd("write", "abcdefghijklmnopqrstuvwxyz123456 x", "Invalid name");
    cmd("fsinfo", "", "RAM only");
    yfs_init(); cmd("ls", "", "(empty)");
    assert(!yfs_command("other", "", capture));
    puts("YoroFS tests passed");
}
