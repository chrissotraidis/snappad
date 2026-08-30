#include "gyro_input_policy.h"

#include <algorithm>
#include <cmath>

namespace snappad {
namespace {

constexpr double kDeadzoneRadiansPerSecond = 0.025;
constexpr double kFullStickRadiansPerSecond = 1.8;

float normalize_rate(double rate, double sensitivity) {
    if (!std::isfinite(rate)) return 0.0f;
    if (!std::isfinite(sensitivity)) sensitivity = kDefaultGyroSensitivity;
    sensitivity = std::clamp(
        sensitivity, kMinimumGyroSensitivity, kMaximumGyroSensitivity);
    const double magnitude = std::abs(rate);
    if (magnitude <= kDeadzoneRadiansPerSecond) return 0.0f;
    const double normalized = sensitivity * (magnitude - kDeadzoneRadiansPerSecond) /
        (kFullStickRadiansPerSecond - kDeadzoneRadiansPerSecond);
    return static_cast<float>(std::copysign(std::min(1.0, normalized), rate));
}

} // namespace

GyroStickInput gyro_rotation_to_stick(
    double rotation_x,
    double rotation_y,
    bool landscape_left,
    double sensitivity,
    bool invert_horizontal,
    bool invert_vertical) {
    const double orientation_sign = landscape_left ? -1.0 : 1.0;
    // Core Motion's rotation direction is opposite the camera direction users
    // expect. Correct that by default, then apply the two explicit inversion
    // preferences independently.
    const double camera_sign = -orientation_sign;
    const double horizontal_sign = invert_horizontal ? -camera_sign : camera_sign;
    const double vertical_sign = invert_vertical ? -camera_sign : camera_sign;
    return {
        normalize_rate(rotation_x * horizontal_sign, sensitivity),
        normalize_rate(rotation_y * vertical_sign, sensitivity),
    };
}

} // namespace snappad
