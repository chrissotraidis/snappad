#include "address_translation.h"

#include <cassert>
#include <cstdint>
#include <vector>

int main() {
    std::vector<std::uint8_t> rdram(0x800000);

    assert(recomp_translate_address(rdram.data(), 0x80000123u)
        == rdram.data() + 0x123);
    assert(recomp_translate_address(rdram.data(), 0xA0000123u)
        == rdram.data() + 0x123);
    assert(recomp_translate_address(rdram.data(), 0xFFFFFFFF80000456ull)
        == rdram.data() + 0x456);

    // Direct boot-integrity probes must resolve to the exact SP boot residue,
    // not to an out-of-range host pointer beyond the RDRAM allocation.
    assert(*reinterpret_cast<std::uint32_t*>(
        recomp_translate_address(rdram.data(), 0xA4000000u)) == 0xFFFFFFFFu);
    assert(*reinterpret_cast<std::uint32_t*>(
        recomp_translate_address(rdram.data(), 0xA4001000u)) == 6103u);
    assert(recomp_translate_address(rdram.data(), 0x04001004u)
        == recomp_translate_address(rdram.data(), 0xA4001004u));

    recomp_context context{};
    context.r4 = 3;
    context.r5 = 0;
    context.r6 = 0x00400321u;
    context.r7 = 0x00123000u;
    osMapTLB_recomp(rdram.data(), &context);
    assert(recomp_translate_address(rdram.data(), 0x00400234u)
        == rdram.data() + 0x123234);

    // The ABI masks the index to the N64's 32 TLB entries.
    context.r4 = 35;
    osUnmapTLB_recomp(rdram.data(), &context);
    return 0;
}
