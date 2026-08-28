#include "accessory_policy.h"

namespace snappad::input {

EmulatedPortPolicy default_emulated_port_policy(std::size_t zero_based_port) {
    if (zero_based_port == 0) {
        return {
            .controller_connected = true,
            .accessory = EmulatedAccessory::None,
        };
    }

    return {};
}

} // namespace snappad::input
