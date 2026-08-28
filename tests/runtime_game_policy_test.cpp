#include "game_registration.h"
#include "n64_input_policy.h"

#include <cstdio>
#include <cstdlib>

namespace {

[[noreturn]] void fail(const char* message) {
    std::fprintf(stderr, "runtime_game_policy_test: %s\n", message);
    std::exit(EXIT_FAILURE);
}

void require(bool condition, const char* message) {
    if (!condition) fail(message);
}

void test_entrypoint(uint8_t*, recomp_context*) {
}

} // namespace

int main() {
    constexpr std::uint64_t rom_hash = 0x0123456789ABCDEFULL;
    constexpr gpr entrypoint_address = 0x80000400;
    const auto game = pokemon_snap::make_game_entry(
        rom_hash,
        "POKEMON SNAP",
        u8"pokemonsnap.n64.us",
        entrypoint_address,
        test_entrypoint);

    require(game.rom_hash == rom_hash, "ROM hash changed during registration");
    require(game.internal_name == "POKEMON SNAP", "internal name changed");
    require(game.game_id == u8"pokemonsnap.n64.us", "game ID changed");
    require(game.save_type == recomp::SaveType::Flashram, "game is not registered as FlashRAM");
    require(game.is_enabled, "game registration is disabled");
    require(!game.has_compressed_code, "unsupported compressed-code path was enabled");
    require(game.decompression_routine == nullptr, "unexpected decompression callback registered");
    require(game.entrypoint_address == entrypoint_address, "entrypoint address changed");
    require(game.entrypoint == test_entrypoint, "entrypoint function changed");
    require(game.on_init_callback == nullptr, "unverified game-specific hook was registered");

    const auto port_one = snappad::input::runtime_connected_device_info(0);
    require(
        port_one.connected_device == ultramodern::input::Device::Controller,
        "runtime port 1 is not a controller");
    require(
        port_one.connected_pak == ultramodern::input::Pak::None,
        "runtime port 1 falsely reports an accessory");

    for (int port : {-1, 1, 2, 3, 99}) {
        const auto info = snappad::input::runtime_connected_device_info(port);
        require(
            info.connected_device == ultramodern::input::Device::None,
            "runtime exposed an unexpected controller port");
        require(
            info.connected_pak == ultramodern::input::Pak::None,
            "runtime exposed an unexpected accessory");
    }

    std::puts("runtime_game_policy_test: registration and device policy passed");
    return EXIT_SUCCESS;
}
