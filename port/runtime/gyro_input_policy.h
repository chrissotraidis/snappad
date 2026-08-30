#pragma once

namespace snappad {

struct GyroStickInput {
    float x;
    float y;
};

constexpr double kDefaultGyroSensitivity = 1.9;
constexpr double kMinimumGyroSensitivity = 0.5;
constexpr double kMaximumGyroSensitivity = 2.5;
constexpr bool kDefaultGyroInvertHorizontal = false;
constexpr bool kDefaultGyroInvertVertical = true;

// Convert bias-corrected Core Motion rotation rates (radians/second) into the
// normalized N64 stick used for camera movement. SnapPad is landscape-only, so
// the two supported orientations differ by a 180-degree axis inversion.
GyroStickInput gyro_rotation_to_stick(
    double rotation_x,
    double rotation_y,
    bool landscape_left,
    double sensitivity,
    bool invert_horizontal,
    bool invert_vertical);

} // namespace snappad
