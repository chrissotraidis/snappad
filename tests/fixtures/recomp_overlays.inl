// Compile-only fixture matching N64Recomp's generated overlay table contract.
#include "librecomp/sections.h"

static SectionTableEntry section_table[] = {
    {
        .rom_addr = 0x1000,
        .ram_addr = 0x80000400,
        .size = 0x40,
        .funcs = nullptr,
        .num_funcs = 0,
        .relocs = nullptr,
        .num_relocs = 0,
        .index = 0,
    },
};
const size_t num_sections = 1;
static int overlay_sections_by_index[] = {-1};
