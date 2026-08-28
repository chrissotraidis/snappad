#pragma once

#include <cstdint>
#include <string>

#include "librecomp/game.hpp"

namespace pokemon_snap {

using RecompiledEntrypoint = void (*)(uint8_t*, recomp_context*);

recomp::GameEntry make_game_entry(
    std::uint64_t rom_xxh3,
    std::string internal_name,
    std::u8string game_id,
    gpr entrypoint_address,
    RecompiledEntrypoint entrypoint);

} // namespace pokemon_snap
