#pragma once

#include "types.h"

/* Minimal string / memory routines (freestanding, no libc). */

void *memset(void *dst, int c, size_t n);
void *memcpy(void *dst, const void *src, size_t n);
void *memmove(void *dst, const void *src, size_t n);

size_t strlen(const char *s);
int strcmp(const char *a, const char *b);
int strncmp(const char *a, const char *b, size_t n);
char *strcpy(char *dst, const char *src);
char *strchr(const char *s, int c);

/* Integer conversion. Returns pointer to buf. */
char *itoa(int value, char *buf);
char *utoa(uint32_t value, char *buf, int base);
int atoi(const char *s);
