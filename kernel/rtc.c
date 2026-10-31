#include "rtc.h"
#include "io.h"

uint8_t cmos_read(uint8_t reg) {
    outb(0x70, reg);
    io_wait();
    return inb(0x71);
}

static uint8_t from_bcd(uint8_t v) {
    return (uint8_t)((v & 0x0F) + (v >> 4) * 10);
}

void rtc_read(struct rtc_time *t) {
    /* Wait until the RTC is not in the middle of an update. */
    while (cmos_read(0x0A) & 0x80)
        ;

    t->second = cmos_read(0x00);
    t->minute = cmos_read(0x02);
    t->hour = cmos_read(0x04);
    t->day = cmos_read(0x07);
    t->month = cmos_read(0x08);
    t->year = cmos_read(0x09);

    uint8_t reg_b = cmos_read(0x0B);

    if (!(reg_b & 0x04)) { /* values are BCD */
        t->second = from_bcd(t->second);
        t->minute = from_bcd(t->minute);
        t->hour = (uint8_t)(from_bcd(t->hour & 0x7F) | (t->hour & 0x80));
        t->day = from_bcd(t->day);
        t->month = from_bcd(t->month);
        t->year = from_bcd((uint8_t)t->year);
    }

    if (!(reg_b & 0x02) && (t->hour & 0x80)) { /* 12-hour format, PM */
        t->hour = (uint8_t)(((t->hour & 0x7F) + 12) % 24);
    } else {
        t->hour &= 0x7F;
    }

    t->year = (uint16_t)(t->year + 2000);
}

uint32_t cmos_total_memory_kb(void) {
    uint32_t base = cmos_read(0x15) | ((uint32_t)cmos_read(0x16) << 8);
    uint32_t ext = cmos_read(0x17) | ((uint32_t)cmos_read(0x18) << 8);
    uint32_t ext_above_16m =
        (cmos_read(0x30) | ((uint32_t)cmos_read(0x31) << 8)) * 64u;
    return base + ext + ext_above_16m;
}
