#pragma once

#include <cstddef>

namespace snappad::input {

enum class EmulatedAccessory {
    None,
    RumblePak,
};

struct EmulatedPortPolicy {
    bool controller_connected = false;
    EmulatedAccessory accessory = EmulatedAccessory::None;
};

// Pokemon Snap is a single-player game. Keep optional N64 accessories absent
// until their behavior has been implemented and observed on the real game.
EmulatedPortPolicy default_emulated_port_policy(std::size_t zero_based_port);

} // namespace snappad::input
