#include "address_translation.h"

#include <array>
#include <cstdint>

namespace {

struct TlbEntry {
    bool valid = false;
    std::uint32_t virtual_base = 0;
    std::uint32_t physical_base = 0;
    std::uint32_t page_size = 0x1000;
};

std::array<TlbEntry, 32> tlb_entries{};

// Pokémon Snap probes the two words left by the N64 boot process before any
// RSP task runs. Most SP operations enter N64ModernRuntime through translated
// OS calls, but these two direct KSEG1 reads still pass through the generated
// memory ABI. Keep a small, aligned SP address window with the exact IPL3
// residue the game validates: -1 in DMEM and 6103 in IMEM.
alignas(4) std::array<std::uint32_t, 0x2000 / sizeof(std::uint32_t)>
    sp_boot_probe_memory = [] {
        std::array<std::uint32_t, 0x2000 / sizeof(std::uint32_t)> memory{};
        memory[0x0000 / sizeof(std::uint32_t)] = 0xFFFFFFFFu;
        memory[0x1000 / sizeof(std::uint32_t)] = 6103u;
        return memory;
    }();

std::uint32_t page_size_from_mask(std::uint32_t page_mask) {
    return ((page_mask | 0x1FFFu) + 1u) >> 1;
}

bool is_rdram_kseg(std::uint32_t address) {
    return (address >= 0x80000000u && address < 0x80800000u)
        || (address >= 0xA0000000u && address < 0xA0800000u);
}

std::uint8_t* translate_sp_memory(std::uint32_t address) {
    const std::uint32_t physical_address = address & 0x1FFFFFFFu;
    if (physical_address < 0x04000000u || physical_address >= 0x04002000u) {
        return nullptr;
    }
    const std::uint32_t offset = physical_address - 0x04000000u;
    return reinterpret_cast<std::uint8_t*>(sp_boot_probe_memory.data()) + offset;
}

} // namespace

extern "C" std::uint8_t* recomp_translate_address(
    std::uint8_t* rdram, gpr address) {
    const std::uint32_t virtual_address = static_cast<std::uint32_t>(address);
    if (is_rdram_kseg(virtual_address)) {
        return rdram + (virtual_address & 0x7FFFFFu);
    }

    if (std::uint8_t* sp_memory = translate_sp_memory(virtual_address)) {
        return sp_memory;
    }

    for (const TlbEntry& entry : tlb_entries) {
        if (!entry.valid) continue;
        const std::uint32_t page_offset = virtual_address - entry.virtual_base;
        if (page_offset < entry.page_size) {
            return rdram + ((entry.physical_base + page_offset) & 0x7FFFFFu);
        }
    }

    // Match the static-recomp ABI fallback for sign-extended KSEG addresses.
    return rdram + (address - 0xFFFFFFFF80000000ull);
}

extern "C" void osMapTLB_recomp(std::uint8_t*, recomp_context* context) {
    const std::uint32_t index = static_cast<std::uint32_t>(context->r4) & 31u;
    const std::uint32_t page_mask = static_cast<std::uint32_t>(context->r5);
    const std::uint32_t page_size = page_size_from_mask(page_mask);
    const std::uint32_t virtual_base =
        static_cast<std::uint32_t>(context->r6) & ~(page_size - 1u);
    const std::uint32_t physical_base =
        static_cast<std::uint32_t>(context->r7) & 0xFFFFFFu;
    tlb_entries[index] = {
        .valid = true,
        .virtual_base = virtual_base,
        .physical_base = physical_base,
        .page_size = page_size,
    };
}

extern "C" void osUnmapTLB_recomp(std::uint8_t*, recomp_context* context) {
    const std::uint32_t index = static_cast<std::uint32_t>(context->r4) & 31u;
    tlb_entries[index] = {};
}
