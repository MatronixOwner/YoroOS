#pragma once
#include <stdint.h>

/* Copied out of UEFI protocols before ExitBootServices. */
struct yoro_framebuffer {
    volatile uint32_t *base;
    uint64_t size;
    uint32_t width, height, stride;
    uint32_t red_mask, green_mask, blue_mask;
};
void yoro_render(const struct yoro_framebuffer *fb);
void yoro_kernel_main(const struct yoro_framebuffer *fb) __attribute__((noreturn));
void yoro_enter_kernel(const struct yoro_framebuffer *fb) __attribute__((noreturn));
