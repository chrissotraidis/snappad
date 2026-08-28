#pragma once

#include <stdint.h>

#include "recomp.h"

#ifdef __cplusplus
extern "C" {
#endif

void __osContRamRead_recomp(uint8_t* rdram, recomp_context* context);
void __osContRamWrite_recomp(uint8_t* rdram, recomp_context* context);
void __osSetWatchLo_recomp(uint8_t* rdram, recomp_context* context);

#ifdef __cplusplus
}
#endif
