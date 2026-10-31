#pragma once

#include "types.h"

/* CMOS / RTC access. */

struct rtc_time {
    uint8_t second;
    uint8_t minute;
    uint8_t hour;
    uint8_t day;
    uint8_t month;
    uint16_t year;
};

uint8_t cmos_read(uint8_t reg);
void rtc_read(struct rtc_time *t);

/* Total conventional+extended memory reported by CMOS, in KiB. */
uint32_t cmos_total_memory_kb(void);
