#pragma once

#include <cstdint>

#include "recomp.h"

extern "C" std::uint8_t* recomp_translate_address(
    std::uint8_t* rdram, gpr address);
extern "C" void osMapTLB_recomp(
    std::uint8_t* rdram, recomp_context* context);
extern "C" void osUnmapTLB_recomp(
    std::uint8_t* rdram, recomp_context* context);
