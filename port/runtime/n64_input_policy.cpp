#include "n64_input_policy.h"

#include "accessory_policy.h"

namespace snappad::input {

ultramodern::input::connected_device_info_t runtime_connected_device_info(
    int zero_based_port) {
    if (zero_based_port < 0) {
        return {
            ultramodern::input::Device::None,
            ultramodern::input::Pak::None,
        };
    }

    const auto policy = default_emulated_port_policy(
        static_cast<std::size_t>(zero_based_port));
    return {
        policy.controller_connected
            ? ultramodern::input::Device::Controller
            : ultramodern::input::Device::None,
        ultramodern::input::Pak::None,
    };
}

} // namespace snappad::input
