#pragma once
#include <stddef.h>

/* Volatile, flat prototype. This is not an on-disk format. */
#define YFS_MAX_FILES 16
#define YFS_NAME_MAX 31
#define YFS_DATA_MAX 511

enum yfs_result { YFS_OK, YFS_INVALID, YFS_FULL, YFS_TOO_LARGE, YFS_NOT_FOUND };
void yfs_init(void);
enum yfs_result yfs_write(const char *name, const char *data);
enum yfs_result yfs_remove(const char *name);
const char *yfs_read(const char *name);
const char *yfs_name_at(size_t index);
/* Return 1 if command is handled; output is supplied by the caller. */
int yfs_command(const char *command, const char *arg, void (*out)(const char *));
