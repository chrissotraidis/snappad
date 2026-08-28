#pragma once

#include <cstdint>

namespace pokemon_snap::generated {

inline constexpr std::uint64_t rom_xxh3 = 0x0123456789ABCDEFULL;
inline constexpr std::uint32_t entrypoint = 0x80000400U;
inline constexpr std::uint32_t sp_imem_ok_vram = 0x800484E0U;
inline constexpr std::uint32_t sp_dmem_ok_vram = 0x800484E1U;
inline constexpr std::uint32_t player_focus_flag_vram = 0x803AE768U;
inline constexpr std::uint32_t player_focus_object_vram = 0x803AE76CU;
inline constexpr std::uint32_t player_focus_subject_vram = 0x803AE770U;
inline constexpr std::uint32_t illegal_copy_player_flag = 21U;
inline constexpr char internal_name[] = "POKEMON SNAP";
inline constexpr char8_t game_id[] = u8"pokemonsnap.n64.us";

} // namespace pokemon_snap::generated
