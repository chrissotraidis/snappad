#include "n64_os_stubs.h"

namespace {

constexpr gpr kPfsErrNoPack = 1;

} // namespace

extern "C" void __osContRamRead_recomp(
    std::uint8_t*, recomp_context* context) {
    // SnapPad's current accessory policy exposes a standard controller with no
    // Controller Pak, Rumble Pak, Transfer Pak, or printer. Low-level PIF RAM
    // probes must agree with the public PFS calls in N64ModernRuntime and report
    // PFS_ERR_NOPACK instead of letting game code infer a phantom accessory.
    context->r2 = kPfsErrNoPack;
}

extern "C" void __osContRamWrite_recomp(
    std::uint8_t*, recomp_context* context) {
    context->r2 = kPfsErrNoPack;
}

extern "C" void __osSetWatchLo_recomp(
    std::uint8_t*, recomp_context*) {
    // The original writes CP0 WatchLo during boot. It only configures a MIPS
    // hardware data watchpoint and has no game-visible state in the AOT host.
}
