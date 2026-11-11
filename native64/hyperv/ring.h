#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define YHV_PAGE_SIZE 4096u
#define YHV_PACKET_INBAND 6u
#define YHV_PACKET_COMPLETION 11u
#define YHV_PACKET_WANT_COMPLETION 1u

/* Hyper-V's ring header occupies an entire shared 4 KiB page. */
struct yhv_ring_header {
    uint32_t write_index, read_index, interrupt_mask, pending_send_size;
    uint32_t reserved[12], feature_bits;
};
struct yhv_packet_header {
    uint16_t type, offset8, length8, flags;
    uint64_t transaction;
};
struct yhv_ring {
    struct yhv_ring_header *header;
    uint8_t *data;
    uint32_t capacity;
};
enum yhv_ring_result { YHV_RING_OK, YHV_RING_EMPTY, YHV_RING_FULL,
                       YHV_RING_INVALID, YHV_RING_BUFFER_SMALL };
bool yhv_ring_init(struct yhv_ring *, void *memory, uint32_t pages);
enum yhv_ring_result yhv_ring_write(struct yhv_ring *, uint16_t type,
    const void *payload, uint32_t len, uint64_t transaction, uint16_t flags,
    bool *notify);
enum yhv_ring_result yhv_ring_read(struct yhv_ring *, struct yhv_packet_header *,
    void *payload, uint32_t cap, uint32_t *length, bool *notify);
