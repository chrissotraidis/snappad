#include "gyro_input_policy.h"

#include <cmath>
#include <cstdio>
#include <cstdlib>

namespace {

[[noreturn]] void fail(const char* message) {
    std::fprintf(stderr, "gyro_input_policy_test: %s\n", message);
    std::exit(EXIT_FAILURE);
}

void require(bool condition, const char* message) {
    if (!condition) fail(message);
}

void require_near(float actual, float expected, const char* message) {
    if (std::abs(actual - expected) > 0.0001f) fail(message);
}

} // namespace

int main() {
    require_near(static_cast<float>(snappad::kDefaultGyroSensitivity), 1.9f,
        "accepted default sensitivity changed");
    require(!snappad::kDefaultGyroInvertHorizontal,
        "accepted horizontal inversion default changed");
    require(snappad::kDefaultGyroInvertVertical,
        "accepted vertical inversion default changed");

    auto input = snappad::gyro_rotation_to_stick(
        0.02, -0.02, false, snappad::kDefaultGyroSensitivity, false, false);
    require_near(input.x, 0.0f, "horizontal deadzone drifted");
    require_near(input.y, 0.0f, "vertical deadzone drifted");

    const auto right = snappad::gyro_rotation_to_stick(
        0.9125, -0.9125, false, 1.0, false, false);
    require_near(right.x, -0.5f, "default horizontal direction was not corrected");
    require_near(right.y, 0.5f, "default vertical direction was not corrected");

    const auto left = snappad::gyro_rotation_to_stick(
        0.9125, -0.9125, true, 1.0, false, false);
    require_near(left.x, 0.5f, "landscape-left horizontal orientation mapped incorrectly");
    require_near(left.y, -0.5f, "landscape-left vertical orientation mapped incorrectly");

    const auto inverted = snappad::gyro_rotation_to_stick(
        0.9125, -0.9125, false, 1.0, true, true);
    require_near(inverted.x, 0.5f, "horizontal inversion did not apply");
    require_near(inverted.y, -0.5f, "vertical inversion did not apply");

    const auto horizontal_only = snappad::gyro_rotation_to_stick(
        0.9125, -0.9125, false, 1.0, true, false);
    require_near(horizontal_only.x, 0.5f, "horizontal-only inversion did not apply");
    require_near(horizontal_only.y, 0.5f, "horizontal inversion changed the vertical axis");

    const auto accepted_defaults = snappad::gyro_rotation_to_stick(
        0.9125, -0.9125, false,
        snappad::kDefaultGyroSensitivity,
        snappad::kDefaultGyroInvertHorizontal,
        snappad::kDefaultGyroInvertVertical);
    require_near(accepted_defaults.x, -0.95f,
        "accepted default horizontal response changed");
    require_near(accepted_defaults.y, -0.95f,
        "accepted default vertical response changed");

    const auto sensitive = snappad::gyro_rotation_to_stick(
        0.46875, -0.46875, false, 2.0, false, false);
    require_near(sensitive.x, -0.5f, "sensitivity did not scale horizontal input");
    require_near(sensitive.y, 0.5f, "sensitivity did not scale vertical input");

    input = snappad::gyro_rotation_to_stick(
        4.0, -4.0, false, 99.0, false, false);
    require_near(input.x, -1.0f, "horizontal gyro rate exceeded full stick");
    require_near(input.y, 1.0f, "vertical gyro rate exceeded full stick");

    input = snappad::gyro_rotation_to_stick(
        INFINITY, NAN, false, NAN, false, false);
    require_near(input.x, 0.0f, "non-finite horizontal input was not neutralized");
    require_near(input.y, 0.0f, "non-finite vertical input was not neutralized");

    require(std::isfinite(input.x) && std::isfinite(input.y),
        "gyro conversion returned a non-finite stick value");
    std::puts("gyro_input_policy_test: all scenarios passed");
    return EXIT_SUCCESS;
}
