#include "cursor.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>

static void run(unsigned w, unsigned h, unsigned stride, int reverse) {
    size_t n=(size_t)stride*h;
    uint32_t *p=malloc((n+2)*4); assert(p);
    for (size_t i=0; i<n+2; ++i) p[i]=0x5a2982cf;
    struct yoro_framebuffer f={p+1,n*4,w,h,stride,reverse?255:0xff0000,0xff00,reverse?0xff0000:255};
    struct yoro_cursor c;
    yoro_cursor_init(&c,&f);
    yoro_cursor_move(&c,w/2,h/2);
    int changed=0; for (size_t i=1;i<=n;++i) if(p[i]!=0x5a2982cf) ++changed;
    assert(changed > 0);
    yoro_cursor_hide(&c);
    for (size_t i=0;i<n+2;++i) assert(p[i]==0x5a2982cf);
    yoro_cursor_move(&c,-1,-1); yoro_cursor_move(&c,(int)w+50,(int)h+50);
    yoro_cursor_move(&c,w/2,h/2); yoro_cursor_hide(&c);
    for (size_t i=0;i<n+2;++i) assert(p[i]==0x5a2982cf);
    f.size=0; yoro_cursor_move(&c,1,1); assert(!c.visible);
    free(p);
}
int main(void) { run(128,100,130,0); run(120,85,120,1); run(8,8,10,0); puts("Cursor draw, clipping and restore tests passed"); }
