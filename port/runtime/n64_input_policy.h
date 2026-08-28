#pragma once

#include "ultramodern/input.hpp"

namespace snappad::input {

ultramodern::input::connected_device_info_t runtime_connected_device_info(
    int zero_based_port);

} // namespace snappad::input
