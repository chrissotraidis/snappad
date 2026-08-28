// Link-only stand-ins for ROM-derived symbols. This target is never executed
// or packaged; it proves SnapPad-owned runner/glue can resolve against the
// native runtime before G1 produces the real entrypoint and audio RSP.
#include <cstdint>

#include "librecomp/rsp.hpp"
#include "recomp.h"

extern "C" void recomp_entrypoint(std::uint8_t*, recomp_context*) {
}

RspExitReason aspMain(std::uint8_t*, std::uint32_t) {
    return RspExitReason::Unsupported;
}
