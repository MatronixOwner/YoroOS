#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

struct yhv_hid_axis { uint32_t offset, size; int64_t minimum, maximum; bool found; };
struct yhv_hid_mouse { struct yhv_hid_axis x, y; uint32_t report_bits; uint8_t report_id; };
struct yhv_pointer { uint32_t x, y; };
/* Parse only supported absolute HID pointer layouts; reject unsupported forms. */
bool yhv_hid_mouse_parse(struct yhv_hid_mouse *, const uint8_t *, size_t);
bool yhv_hid_mouse_decode(const struct yhv_hid_mouse *, const uint8_t *, size_t,
                          uint32_t width, uint32_t height, struct yhv_pointer *);

/* Synthetic HID-over-VMBus wire message handling. This code alone does not
 * connect to VMBus, send replies or receive physical mouse input. */
struct yhv_mouse { struct yhv_hid_mouse hid; bool accepted, ready; };
enum yhv_mouse_event { YHV_MOUSE_INVALID, YHV_MOUSE_IGNORED, YHV_MOUSE_ACCEPTED,
                       YHV_MOUSE_REJECTED, YHV_MOUSE_DEVICE_INFO, YHV_MOUSE_MOVE };
void yhv_mouse_reset(struct yhv_mouse *);
size_t yhv_mouse_protocol_request(uint8_t *out, size_t capacity);
size_t yhv_mouse_device_ack(uint8_t *out, size_t capacity);
enum yhv_mouse_event yhv_mouse_message(struct yhv_mouse *, const uint8_t *, size_t,
                                       uint32_t width, uint32_t height, struct yhv_pointer *);
