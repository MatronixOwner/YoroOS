#include "bootinfo.h"
#include <assert.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdio.h>

static void check(unsigned w, unsigned h, unsigned stride, unsigned size_delta, int reverse) {
    size_t n = (size_t)stride*h;
    uint32_t *pixels = malloc((n+2)*sizeof(*pixels)); assert(pixels);
    for (size_t i=0; i<n+2; ++i) pixels[i]=0xdeadbeef;
    struct yoro_framebuffer f = {pixels+1, n*4-size_delta, w,h,stride,
        reverse ? 0xffu : 0xff0000u,0xff00u, reverse ? 0xff0000u : 0xffu};
    yoro_render(&f);
    assert(pixels[0]==0xdeadbeef && pixels[n+1]==0xdeadbeef);
    if (!size_delta) {
        assert(pixels[1] != 0xdeadbeef);
        for (unsigned y=0; y<h; ++y) for (unsigned x=w; x<stride; ++x)
            assert(pixels[1+(size_t)y*stride+x] == 0xdeadbeef);
    } else assert(pixels[1] == 0xdeadbeef);
    free(pixels);
}
int main(void) {
    check(1024,768,1024,0,0); check(800,600,832,0,1);
    check(100,70,100,0,0); check(640,480,640,4,0);
    yoro_render(NULL);
    puts("Native graphics bounds tests passed");
}
