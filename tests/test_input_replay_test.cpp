#include "test_input_replay.h"

#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <string>

namespace {

[[noreturn]] void fail(const char* message) {
    std::fprintf(stderr, "test_input_replay_test: %s\n", message);
    std::exit(EXIT_FAILURE);
}

void require(bool condition, const char* message) {
    if (!condition) fail(message);
}

void require_near(float actual, float expected, const char* message) {
    if (std::abs(actual - expected) > 0.001f) fail(message);
}

} // namespace

int main() {
    std::string error;
    auto replay = snappad::testing::TestInputReplay::parse(
        "wait:2, start:1, a+stick_right:2, neutral:1", error);
    require(replay.has_value(), "valid route was rejected");
    require(error.empty(), "valid route reported an error");
    require(replay->step_count() == 4, "step count is incorrect");
    require(replay->total_polls() == 6, "poll count is incorrect");

    auto frame = replay->next();
    require(frame.buttons == 0, "wait step pressed a button");
    require(replay->next().buttons == 0, "wait step ended early");
    require(replay->next().buttons == 0x1000, "start step used the wrong bit");
    frame = replay->next();
    require(frame.buttons == 0x8000, "combined action missed A");
    require_near(frame.stick_x, 1.0f, "combined action missed right stick");
    frame = replay->next();
    require(frame.buttons == 0x8000, "multi-poll action ended early");
    require(replay->next().buttons == 0, "neutral step was not neutral");
    require(replay->consume_completed(), "completion edge was not reported");
    require(!replay->consume_completed(), "completion edge repeated");
    require(replay->next().buttons == 0, "finished replay was not neutral");

    require(!snappad::testing::TestInputReplay::parse("start:0", error),
        "zero-length step was accepted");
    require(!snappad::testing::TestInputReplay::parse("stick_left+stick_right:1", error),
        "conflicting stick actions were accepted");

    auto file_route = snappad::testing::TestInputReplay::parse("wait:2,a:1\n", error);
    require(file_route.has_value(), "route file trailing newline was rejected");
    require(file_route->total_polls() == 3, "route file poll count was parsed incorrectly");
    require(!snappad::testing::TestInputReplay::parse("launch_camera:1", error),
        "unknown action was accepted");
    require(!snappad::testing::TestInputReplay::parse("wait:1000001", error),
        "oversized step was accepted");

    std::puts("test_input_replay_test: all scenarios passed");
    return EXIT_SUCCESS;
}
