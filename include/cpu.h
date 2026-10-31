#pragma once

/* CPUID helpers. */

void cpu_get_vendor(char out[13]);  /* e.g. "GenuineIntel" */
void cpu_get_brand(char out[49]);   /* e.g. "Intel(R) Core(TM) ..." */
