#pragma once

#include <cstddef>
#include <cstdint>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

namespace snappad::testing {

struct ReplayFrame {
    std::uint16_t buttons = 0;
    float stick_x = 0.0f;
    float stick_y = 0.0f;
};

class TestInputReplay {
public:
    static std::optional<TestInputReplay> parse(
        std::string_view specification, std::string& error);

    ReplayFrame next();
    bool consume_completed();
    std::size_t step_count() const;
    std::uint64_t total_polls() const;

private:
    struct Step {
        ReplayFrame frame;
        std::uint32_t polls = 0;
    };

    explicit TestInputReplay(std::vector<Step> steps, std::uint64_t total_polls);

    std::vector<Step> steps_;
    std::size_t step_index_ = 0;
    std::uint32_t polls_remaining_ = 0;
    std::uint64_t total_polls_ = 0;
    bool completed_pending_ = false;
};

} // namespace snappad::testing
