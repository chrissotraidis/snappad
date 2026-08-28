#include "accessory_policy.h"

#include <cstdio>
#include <cstdlib>

namespace {

[[noreturn]] void fail(const char* message) {
    std::fprintf(stderr, "accessory_policy_test: %s\n", message);
    std::exit(EXIT_FAILURE);
}

void require(bool condition, const char* message) {
    if (!condition) fail(message);
}

} // namespace

int main() {
    const auto player_one = snappad::input::default_emulated_port_policy(0);
    require(player_one.controller_connected, "port 1 must expose a standard controller");
    require(
        player_one.accessory == snappad::input::EmulatedAccessory::None,
        "port 1 must not claim an unimplemented accessory");

    for (std::size_t port = 1; port < 4; ++port) {
        const auto policy = snappad::input::default_emulated_port_policy(port);
        require(!policy.controller_connected, "ports 2 through 4 must be absent");
        require(
            policy.accessory == snappad::input::EmulatedAccessory::None,
            "absent ports must not expose an accessory");
    }

    const auto invalid_port = snappad::input::default_emulated_port_policy(99);
    require(!invalid_port.controller_connected, "an out-of-range port must be absent");
    require(
        invalid_port.accessory == snappad::input::EmulatedAccessory::None,
        "an out-of-range port must not expose an accessory");

    std::puts("accessory_policy_test: all scenarios passed");
    return EXIT_SUCCESS;
}
