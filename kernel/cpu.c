#include "cpu.h"
#include "types.h"
#include "string.h"

static void cpuid(uint32_t leaf, uint32_t *eax, uint32_t *ebx, uint32_t *ecx,
                  uint32_t *edx) {
    __asm__ volatile("cpuid"
                     : "=a"(*eax), "=b"(*ebx), "=c"(*ecx), "=d"(*edx)
                     : "a"(leaf));
}

void cpu_get_vendor(char out[13]) {
    uint32_t eax, ebx, ecx, edx;
    cpuid(0, &eax, &ebx, &ecx, &edx);
    memcpy(out + 0, &ebx, 4);
    memcpy(out + 4, &edx, 4);
    memcpy(out + 8, &ecx, 4);
    out[12] = '\0';
}

void cpu_get_brand(char out[49]) {
    uint32_t eax, ebx, ecx, edx;
    cpuid(0x80000000u, &eax, &ebx, &ecx, &edx);
    if (eax < 0x80000004u) {
        strcpy(out, "(brand string not available)");
        return;
    }
    uint32_t *p = (uint32_t *)out;
    cpuid(0x80000002u, p + 0, p + 1, p + 2, p + 3);
    cpuid(0x80000003u, p + 4, p + 5, p + 6, p + 7);
    cpuid(0x80000004u, p + 8, p + 9, p + 10, p + 11);
    out[48] = '\0';
}
