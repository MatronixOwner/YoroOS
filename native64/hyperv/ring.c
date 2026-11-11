/* Hyper-V VMBus ring protocol, little-endian x86-64. Shared by host tests. */
#include "ring.h"
#include <limits.h>

_Static_assert(sizeof(struct yhv_packet_header)==16, "VMBus packet descriptor");
static uint32_t used(uint32_t rd, uint32_t wr, uint32_t cap) {
    return wr >= rd ? wr-rd : cap-rd+wr;
}
static void copy_in(struct yhv_ring *r, uint32_t off, const void *src, uint32_t n) {
    const uint8_t *p=src;
    for (uint32_t i=0; i<n; ++i) { r->data[off]=p[i]; if (++off==r->capacity) off=0; }
}
static void copy_out(const struct yhv_ring *r, uint32_t off, void *dst, uint32_t n) {
    uint8_t *p=dst;
    for (uint32_t i=0; i<n; ++i) { p[i]=r->data[off]; if (++off==r->capacity) off=0; }
}
static uint32_t advance(const struct yhv_ring *r, uint32_t at, uint32_t n) {
    return (uint32_t)(((uint64_t)at+n)%r->capacity);
}
static bool valid(const struct yhv_ring *r) {
    return r && r->header && r->data && r->capacity >= YHV_PAGE_SIZE;
}
bool yhv_ring_init(struct yhv_ring *r, void *memory, uint32_t pages) {
    if (!r || !memory || pages < 2 || pages > UINT32_MAX / YHV_PAGE_SIZE) return false;
    r->header=memory; r->data=(uint8_t *)memory+YHV_PAGE_SIZE;
    r->capacity=(pages-1)*YHV_PAGE_SIZE;
    for (uint32_t i=0; i<YHV_PAGE_SIZE; ++i) ((uint8_t *)memory)[i]=0;
    r->header->feature_bits=1;
    return true;
}
enum yhv_ring_result yhv_ring_write(struct yhv_ring *r, uint16_t type,
    const void *data, uint32_t len, uint64_t id, uint16_t flags, bool *notify) {
    if (notify) *notify=false;
    if (!valid(r) || (len && !data) || len > 524256u) return YHV_RING_INVALID;
    uint32_t padded=(len+7u)&~7u, total=16u+padded+8u;
    if (total >= r->capacity || (16u+padded)/8u > UINT16_MAX) return YHV_RING_INVALID;
    uint32_t wr=__atomic_load_n(&r->header->write_index,__ATOMIC_RELAXED);
    uint32_t rd=__atomic_load_n(&r->header->read_index,__ATOMIC_ACQUIRE);
    if (wr>=r->capacity || rd>=r->capacity) return YHV_RING_INVALID;
    if (r->capacity-used(rd,wr,r->capacity) <= total) return YHV_RING_FULL;
    struct yhv_packet_header header={type,2,(uint16_t)((16+padded)/8),flags,id};
    uint64_t zero=0, trailer=(uint64_t)wr << 32;
    uint32_t at=wr;
    copy_in(r,at,&header,16); at=advance(r,at,16);
    if (len) copy_in(r,at,data,len);
    at=advance(r,at,len);
    if (padded>len) copy_in(r,at,&zero,padded-len);
    at=advance(r,at,padded-len);
    copy_in(r,at,&trailer,8); at=advance(r,at,8);
    __atomic_store_n(&r->header->write_index,at,__ATOMIC_RELEASE);
    __atomic_thread_fence(__ATOMIC_SEQ_CST);
    if (notify) *notify=!__atomic_load_n(&r->header->interrupt_mask,__ATOMIC_ACQUIRE);
    return YHV_RING_OK;
}
enum yhv_ring_result yhv_ring_read(struct yhv_ring *r, struct yhv_packet_header *header,
    void *data, uint32_t cap, uint32_t *len, bool *notify) {
    if (notify) *notify=false;
    if (!valid(r) || !header || !len || (cap && !data)) return YHV_RING_INVALID;
    uint32_t rd=__atomic_load_n(&r->header->read_index,__ATOMIC_RELAXED);
    uint32_t wr=__atomic_load_n(&r->header->write_index,__ATOMIC_ACQUIRE);
    if (rd>=r->capacity || wr>=r->capacity) return YHV_RING_INVALID;
    uint32_t n=used(rd,wr,r->capacity);
    if (!n) return YHV_RING_EMPTY;
    if (n<24) return YHV_RING_INVALID;
    copy_out(r,rd,header,16);
    uint32_t off=(uint32_t)header->offset8*8u, total=(uint32_t)header->length8*8u;
    if (off<16 || total<off || total+8u>n || total+8u>=r->capacity) return YHV_RING_INVALID;
    *len=total-off;
    if (*len>cap) return YHV_RING_BUFFER_SMALL; /* Leave the packet for retry. */
    if (*len) copy_out(r,advance(r,rd,off),data,*len);
    rd=advance(r,rd,total+8u);
    __atomic_store_n(&r->header->read_index,rd,__ATOMIC_RELEASE);
    __atomic_thread_fence(__ATOMIC_SEQ_CST);
    uint32_t need=__atomic_load_n(&r->header->pending_send_size,__ATOMIC_ACQUIRE);
    wr=__atomic_load_n(&r->header->write_index,__ATOMIC_ACQUIRE);
    if (notify && wr<r->capacity) *notify=need && r->capacity-used(rd,wr,r->capacity)>=need;
    return YHV_RING_OK;
}
