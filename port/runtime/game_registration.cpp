#include "game_registration.h"

#include <utility>

namespace pokemon_snap {

recomp::GameEntry make_game_entry(
    std::uint64_t rom_xxh3,
    std::string internal_name,
    std::u8string game_id,
    gpr entrypoint_address,
    RecompiledEntrypoint entrypoint) {
    return {
        .rom_hash = rom_xxh3,
        .internal_name = std::move(internal_name),
        .game_id = std::move(game_id),
        .mod_game_id = "",
        .save_type = recomp::SaveType::Flashram,
        .is_enabled = true,
        .decompression_routine = nullptr,
        .has_compressed_code = false,
        .entrypoint_address = entrypoint_address,
        .entrypoint = entrypoint,
        .thread_create_callback = nullptr,
        .on_init_callback = nullptr,
    };
}

} // namespace pokemon_snap
