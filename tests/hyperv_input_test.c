#include "ring.h"
#include "mouse.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

/* Common absolute-pointer report descriptor: 5 buttons, X/Y at 0..32767,
   and a signed wheel. No device is contacted by these tests. */
static const uint8_t descriptor[]={
  0x05,0x01,0x09,0x02,0xa1,0x01,0x09,0x01,0xa1,0x00,0x05,0x09,0x19,0x01,0x29,0x05,
  0x15,0x00,0x25,0x01,0x95,0x05,0x75,0x01,0x81,0x02,0x95,0x01,0x75,0x03,0x81,0x01,
  0x05,0x01,0x09,0x30,0x09,0x31,0x15,0x00,0x26,0xff,0x7f,0x75,0x10,0x95,0x02,0x81,0x02,
  0x09,0x38,0x15,0x81,0x25,0x7f,0x75,0x08,0x95,0x01,0x81,0x06,0xc0,0xc0};
static void put32(uint8_t *b,uint32_t n) { for(int i=0;i<4;++i) b[i]=(uint8_t)(n>>(8*i)); }
static void ring_test(void) {
    static uint8_t mem[3*4096]; struct yhv_ring r; struct yhv_packet_header hdr;
    uint8_t out[256], src[23]; for(unsigned i=0;i<sizeof(src);++i)src[i]=(uint8_t)(i+1);
    uint32_t n; bool signal;
    assert(!yhv_ring_init(&r,mem,1)); assert(yhv_ring_init(&r,mem,3));
    assert(yhv_ring_read(&r,&hdr,out,sizeof out,&n,&signal)==YHV_RING_EMPTY);
    assert(yhv_ring_write(&r,YHV_PACKET_INBAND,src,sizeof src,123,1,&signal)==YHV_RING_OK && signal);
    assert(yhv_ring_read(&r,&hdr,out,4,&n,&signal)==YHV_RING_BUFFER_SMALL && n==24);
    assert(yhv_ring_read(&r,&hdr,out,sizeof out,&n,&signal)==YHV_RING_OK);
    assert(n==24 && hdr.transaction==123 && !memcmp(src,out,sizeof src) && out[23]==0);
    r.header->write_index=r.capacity-10; r.header->read_index=r.capacity-10;
    assert(yhv_ring_write(&r,6,src,sizeof src,42,0,&signal)==YHV_RING_OK);
    assert(yhv_ring_read(&r,&hdr,out,sizeof out,&n,&signal)==YHV_RING_OK);
    assert(hdr.transaction==42 && !memcmp(src,out,sizeof src));
    for (int i=0;i<100;++i) assert(yhv_ring_write(&r,6,src,sizeof src,i,0,&signal)==YHV_RING_OK);
    for (int i=0;i<100;++i) { assert(yhv_ring_read(&r,&hdr,out,sizeof out,&n,&signal)==YHV_RING_OK); assert(hdr.transaction==(uint64_t)i); }
    while (yhv_ring_write(&r,6,src,sizeof src,0,0,&signal)==YHV_RING_OK) {}
    assert(yhv_ring_write(&r,6,src,sizeof src,0,0,&signal)==YHV_RING_FULL);
    assert(yhv_ring_init(&r,mem,3)); r.header->write_index=24;
    memset(r.data,0,24); assert(yhv_ring_read(&r,&hdr,out,sizeof out,&n,&signal)==YHV_RING_INVALID);
    assert(r.header->read_index==0); r.header->write_index=r.capacity;
    assert(yhv_ring_read(&r,&hdr,out,sizeof out,&n,&signal)==YHV_RING_INVALID);
    puts("VMBus ring: wrap, bounds, full and malformed packets passed");
}
static void mouse_test(void) {
    struct yhv_hid_mouse hid; struct yhv_pointer pos;
    uint8_t report[]={1,0xff,0x3f,0x00,0x40,0xff};
    assert(yhv_hid_mouse_parse(&hid,descriptor,sizeof descriptor));
    assert(yhv_hid_mouse_decode(&hid,report,sizeof report,1024,768,&pos));
    assert(pos.x==511 && pos.y==383);
    assert(!yhv_hid_mouse_decode(&hid,report,2,1024,768,&pos));
    assert(!yhv_hid_mouse_parse(&hid,descriptor,sizeof descriptor-3));
    uint8_t rel[sizeof descriptor]; memcpy(rel,descriptor,sizeof rel);
    /* Locate and replace the X/Y input's flags (relative rather than absolute). */
    for(size_t i=32;i+1<sizeof rel;++i) if(rel[i]==0x81 && rel[i+1]==0x02) { rel[i+1]=0x06; break; }
    assert(!yhv_hid_mouse_parse(&hid,rel,sizeof rel));
    struct yhv_mouse m; yhv_mouse_reset(&m); uint8_t msg[256]={0}, tmp[24];
    assert(yhv_mouse_protocol_request(tmp,sizeof tmp)==20 && tmp[18]==2);
    assert(yhv_mouse_device_ack(tmp,16)==0 && yhv_mouse_device_ack(tmp,sizeof tmp)==17);
    put32(msg,1); put32(msg+4,13); put32(msg+8,1); put32(msg+12,5); put32(msg+16,0x20000); msg[20]=1;
    assert(yhv_mouse_message(&m,msg,21,1024,768,&pos)==YHV_MOUSE_ACCEPTED);
    memset(msg,0,sizeof msg); put32(msg,1); put32(msg+8,2);
    unsigned body=32+9+sizeof descriptor; put32(msg+4,8+body); put32(msg+12,body);
    uint8_t *hd=msg+16+32; hd[0]=9;hd[1]=0x21;hd[5]=1;hd[6]=0x22;hd[7]=sizeof descriptor;
    memcpy(hd+9,descriptor,sizeof descriptor);
    assert(yhv_mouse_message(&m,msg,16+body,1024,768,&pos)==YHV_MOUSE_DEVICE_INFO && m.ready);
    memset(msg,0,sizeof msg); put32(msg,1); put32(msg+4,14);put32(msg+8,4);put32(msg+12,6);memcpy(msg+16,report,6);
    assert(yhv_mouse_message(&m,msg,22,1024,768,&pos)==YHV_MOUSE_MOVE && pos.x==511 && pos.y==383);
    assert(yhv_mouse_message(&m,msg,21,1024,768,&pos)==YHV_MOUSE_INVALID);
    put32(msg+12,7); assert(yhv_mouse_message(&m,msg,22,1024,768,&pos)==YHV_MOUSE_INVALID);
    /* Exercise the same report through the ring, including eight-byte padding. */
    static uint8_t memory[2*4096]; struct yhv_ring r; struct yhv_packet_header header;
    uint32_t length=0; bool notify=false; uint8_t payload[256];
    put32(msg+12,6);
    assert(yhv_ring_init(&r,memory,2));
    assert(yhv_ring_write(&r,YHV_PACKET_INBAND,msg,22,88,0,&notify)==YHV_RING_OK);
    assert(yhv_ring_read(&r,&header,payload,sizeof payload,&length,&notify)==YHV_RING_OK);
    assert(header.type==YHV_PACKET_INBAND && length==24);
    assert(yhv_mouse_message(&m,payload,length,1024,768,&pos)==YHV_MOUSE_MOVE && pos.x==511 && pos.y==383);
    /* Deterministic random malformed descriptors and packets must not crash. */
    uint32_t rng=0x821f2a19; uint8_t fuzz[96];
    for (unsigned t=0;t<10000;++t) {
        for (unsigned i=0;i<sizeof fuzz;++i) { rng^=rng<<13; rng^=rng>>17; rng^=rng<<5; fuzz[i]=(uint8_t)rng; }
        (void)yhv_hid_mouse_parse(&hid,fuzz,t%sizeof fuzz);
        (void)yhv_mouse_message(&m,fuzz,t%sizeof fuzz,1024,768,&pos);
    }
    puts("Hyper-V HID: protocol, descriptor, report and malformed data passed");
}
int main(void) { ring_test(); mouse_test(); }
