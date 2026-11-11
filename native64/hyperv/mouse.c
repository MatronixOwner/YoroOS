/* A deliberately limited, bounds-checked HID parser for absolute pointers.
 * Relative mice, mixed report IDs, and complex descriptors are rejected. */
#include "mouse.h"
static uint32_t le(const uint8_t *p, unsigned n) {
    uint32_t v=0; for (unsigned i=0; i<n; ++i) v|=(uint32_t)p[i]<<(8*i); return v;
}
static int64_t signed_value(uint32_t v, unsigned n) {
    if (!n) return 0;
    unsigned bits=n*8;
    return (v & (1u<<(bits-1))) ? (int64_t)v - (int64_t)(1ULL<<bits) : (int64_t)v;
}
static void zero(void *p, size_t n) { for (size_t i=0;i<n;++i) ((uint8_t *)p)[i]=0; }
bool yhv_hid_mouse_parse(struct yhv_hid_mouse *out, const uint8_t *d, size_t len) {
    if (!out || !d || !len || len>4096) return false;
    struct yhv_hid_mouse h; zero(&h,sizeof(h));
    uint32_t page=0, sz=0, count=0, usages[32], nu=0, umin=0, umax=0;
    bool have_min=false,have_max=false, saw_id=false;
    int64_t min=0,max=0;
    unsigned collection_depth=0;
    for (size_t pos=0; pos<len;) {
        uint8_t prefix=d[pos++];
        if (prefix==0xfe) return false; /* Long HID items unsupported. */
        unsigned n=prefix&3u; if (n==3) n=4;
        if (n>len-pos) return false;
        uint32_t v=le(d+pos,n); pos+=n;
        unsigned type=(prefix>>2)&3u, tag=(prefix>>4)&15u;
        if (type==1) { /* Global */
            switch(tag) {
            case 0: page=v; break;
            case 1: min=signed_value(v,n); break;
            case 2: max=min<0?signed_value(v,n):(int64_t)v; break;
            case 7: sz=v; break;
            case 8: if (!v || v>255 || (saw_id && h.report_id!=v) || h.report_bits) return false;
                    h.report_id=(uint8_t)v; saw_id=true; break;
            case 9: count=v; break;
            case 10: case 11: return false; /* Global stack unsupported. */
            default: break;
            }
        } else if (type==2) { /* Local */
            if (tag==0) { if (nu>=32) return false; usages[nu++]=v; }
            else if (tag==1) { umin=v; have_min=true; }
            else if (tag==2) { umax=v; have_max=true; }
        } else if (type==0) { /* Main */
            if (tag==10) { if (++collection_depth>32) return false; }
            if (tag==12) { if (!collection_depth) return false; --collection_depth; }
            if (tag==8) { /* Input, including padding. */
                if (!sz || !count || sz>32 || count>128 || sz*count>4096-h.report_bits) return false;
                bool constant=(v&1)!=0, variable=(v&2)!=0, relative=(v&4)!=0;
                for (uint32_t i=0; i<count; ++i) {
                    uint32_t u=i<nu?usages[i]:(have_min&&have_max&&(uint64_t)umin+i<=umax?umin+i:0);
                    if (!constant && variable && page==1 && (u==0x30 || u==0x31)) {
                        if (relative || max<=min) return false;
                        struct yhv_hid_axis *a=u==0x30?&h.x:&h.y;
                        if (a->found) return false;
                        a->offset=h.report_bits+i*sz; a->size=sz; a->minimum=min; a->maximum=max; a->found=true;
                    }
                }
                h.report_bits+=sz*count;
            }
            nu=0; have_min=false; have_max=false; umin=umax=0;
        }
    }
    if (collection_depth || !h.x.found || !h.y.found) return false;
    *out=h; return true;
}
static uint32_t bits(const uint8_t *d, uint32_t offset, uint32_t size) {
    uint32_t v=0; for (uint32_t i=0;i<size;++i)
        if (d[(offset+i)/8] & (1u<<((offset+i)%8))) v|=1u<<i;
    return v;
}
static uint32_t scale_axis(const uint8_t *p, const struct yhv_hid_axis *a, uint32_t span) {
    uint32_t raw=bits(p,a->offset,a->size);
    int64_t value=raw;
    if (a->minimum<0 && (raw & (1u<<(a->size-1)))) value-=(int64_t)(1ULL<<a->size);
    if (value<a->minimum) value=a->minimum;
    if (value>a->maximum) value=a->maximum;
    return (uint32_t)(((uint64_t)(value-a->minimum)*(span-1))/(uint64_t)(a->maximum-a->minimum));
}
bool yhv_hid_mouse_decode(const struct yhv_hid_mouse *h, const uint8_t *p, size_t len,
                          uint32_t width, uint32_t height, struct yhv_pointer *out) {
    if (!h || !p || !out || !width || !height || !h->x.found || !h->y.found) return false;
    if (h->report_id) { if (!len || *p!=h->report_id) return false; ++p; --len; }
    if (h->report_bits>4096 || len<(h->report_bits+7u)/8u || !h->x.size || !h->y.size ||
        h->x.size>32 || h->y.size>32 || h->x.offset+h->x.size>h->report_bits ||
        h->y.offset+h->y.size>h->report_bits || h->x.maximum<=h->x.minimum || h->y.maximum<=h->y.minimum) return false;
    out->x=scale_axis(p,&h->x,width); out->y=scale_axis(p,&h->y,height); return true;
}
void yhv_mouse_reset(struct yhv_mouse *m) { if (m) zero(m,sizeof(*m)); }
static size_t emit(uint8_t *out, size_t capacity, const uint8_t *p, size_t n) {
    if (!out || capacity<n) return 0;
    for(size_t i=0;i<n;++i) out[i]=p[i];
    return n;
}
size_t yhv_mouse_protocol_request(uint8_t *out, size_t cap) {
    const uint8_t request[]={1,0,0,0, 12,0,0,0, 0,0,0,0, 4,0,0,0, 0,0,2,0};
    return emit(out,cap,request,sizeof(request));
}
size_t yhv_mouse_device_ack(uint8_t *out, size_t cap) {
    const uint8_t ack[]={1,0,0,0, 9,0,0,0, 3,0,0,0, 1,0,0,0, 0};
    return emit(out,cap,ack,sizeof(ack));
}
enum yhv_mouse_event yhv_mouse_message(struct yhv_mouse *m, const uint8_t *p, size_t len,
                                       uint32_t w, uint32_t h, struct yhv_pointer *out) {
    if (!m || !p || len<16 || le(p,4)!=1) return YHV_MOUSE_INVALID;
    uint32_t pipe_len=le(p+4,4), type=le(p+8,4), size=le(p+12,4);
    if (pipe_len<8 || pipe_len>len-8 || size>pipe_len-8) return YHV_MOUSE_INVALID;
    const uint8_t *body=p+16;
    if (type==1) {
        if (size<5 || le(body,4)!=0x00020000u) return YHV_MOUSE_INVALID;
        m->accepted=body[4]!=0; m->ready=false;
        return m->accepted?YHV_MOUSE_ACCEPTED:YHV_MOUSE_REJECTED;
    }
    if (type==2) {
        if (!m->accepted || size<41) return YHV_MOUSE_INVALID;
        const uint8_t *desc=body+32;
        uint32_t descriptor_len=desc[0], report_len=le(desc+7,2);
        if (descriptor_len<9 || descriptor_len>size-32 || report_len>size-32-descriptor_len || desc[1]!=0x21 || desc[6]!=0x22) return YHV_MOUSE_INVALID;
        struct yhv_hid_mouse parsed;
        if (!yhv_hid_mouse_parse(&parsed,desc+descriptor_len,report_len)) { m->ready=false; return YHV_MOUSE_INVALID; }
        m->hid=parsed; m->ready=true; return YHV_MOUSE_DEVICE_INFO;
    }
    if (type==4) {
        if (!m->ready || !yhv_hid_mouse_decode(&m->hid,body,size,w,h,out)) return YHV_MOUSE_INVALID;
        return YHV_MOUSE_MOVE;
    }
    return YHV_MOUSE_IGNORED;
}
