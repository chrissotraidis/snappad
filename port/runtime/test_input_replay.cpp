#include "test_input_replay.h"

#include <charconv>
#include <limits>
#include <utility>

namespace snappad::testing {
namespace {

constexpr std::uint16_t kA = 0x8000;
constexpr std::uint16_t kB = 0x4000;
constexpr std::uint16_t kZ = 0x2000;
constexpr std::uint16_t kStart = 0x1000;
constexpr std::uint16_t kDUp = 0x0800;
constexpr std::uint16_t kDDown = 0x0400;
constexpr std::uint16_t kDLeft = 0x0200;
constexpr std::uint16_t kDRight = 0x0100;
constexpr std::uint16_t kL = 0x0020;
constexpr std::uint16_t kR = 0x0010;
constexpr std::uint16_t kCUp = 0x0008;
constexpr std::uint16_t kCDown = 0x0004;
constexpr std::uint16_t kCLeft = 0x0002;
constexpr std::uint16_t kCRight = 0x0001;

constexpr std::size_t kMaximumSpecificationBytes = 64 * 1024;
constexpr std::size_t kMaximumSteps = 4096;
constexpr std::uint32_t kMaximumStepPolls = 1'000'000;
constexpr std::uint64_t kMaximumTotalPolls = 10'000'000;

std::string_view trim(std::string_view value) {
    while (!value.empty()
        && (value.front() == ' ' || value.front() == '\t'
            || value.front() == '\r' || value.front() == '\n')) {
        value.remove_prefix(1);
    }
    while (!value.empty()
        && (value.back() == ' ' || value.back() == '\t'
            || value.back() == '\r' || value.back() == '\n')) {
        value.remove_suffix(1);
    }
    return value;
}

bool add_action(std::string_view action, ReplayFrame& frame, std::string& error) {
    if (action == "a") frame.buttons |= kA;
    else if (action == "b") frame.buttons |= kB;
    else if (action == "z") frame.buttons |= kZ;
    else if (action == "start") frame.buttons |= kStart;
    else if (action == "l") frame.buttons |= kL;
    else if (action == "r") frame.buttons |= kR;
    else if (action == "d_up") frame.buttons |= kDUp;
    else if (action == "d_down") frame.buttons |= kDDown;
    else if (action == "d_left") frame.buttons |= kDLeft;
    else if (action == "d_right") frame.buttons |= kDRight;
    else if (action == "c_up") frame.buttons |= kCUp;
    else if (action == "c_down") frame.buttons |= kCDown;
    else if (action == "c_left") frame.buttons |= kCLeft;
    else if (action == "c_right") frame.buttons |= kCRight;
    else if (action == "stick_up") {
        if (frame.stick_y != 0.0f) { error = "conflicting vertical stick actions"; return false; }
        frame.stick_y = 1.0f;
    }
    else if (action == "stick_down") {
        if (frame.stick_y != 0.0f) { error = "conflicting vertical stick actions"; return false; }
        frame.stick_y = -1.0f;
    }
    else if (action == "stick_left") {
        if (frame.stick_x != 0.0f) { error = "conflicting horizontal stick actions"; return false; }
        frame.stick_x = -1.0f;
    }
    else if (action == "stick_right") {
        if (frame.stick_x != 0.0f) { error = "conflicting horizontal stick actions"; return false; }
        frame.stick_x = 1.0f;
    }
    else {
        error = "unknown action: " + std::string(action);
        return false;
    }
    return true;
}

} // namespace

TestInputReplay::TestInputReplay(std::vector<Step> steps, std::uint64_t total_polls)
    : steps_(std::move(steps)),
      polls_remaining_(steps_.empty() ? 0 : steps_.front().polls),
      total_polls_(total_polls) {
}

std::optional<TestInputReplay> TestInputReplay::parse(
    std::string_view specification, std::string& error) {
    error.clear();
    if (specification.empty()) {
        error = "route is empty";
        return std::nullopt;
    }
    if (specification.size() > kMaximumSpecificationBytes) {
        error = "route exceeds 64 KiB";
        return std::nullopt;
    }

    std::vector<Step> steps;
    std::uint64_t total_polls = 0;
    std::size_t cursor = 0;
    while (cursor <= specification.size()) {
        const std::size_t comma = specification.find(',', cursor);
        const std::size_t end = comma == std::string_view::npos ? specification.size() : comma;
        const std::string_view token = trim(specification.substr(cursor, end - cursor));
        if (token.empty()) {
            error = "route contains an empty step";
            return std::nullopt;
        }
        if (steps.size() == kMaximumSteps) {
            error = "route exceeds 4096 steps";
            return std::nullopt;
        }

        const std::size_t colon = token.rfind(':');
        if (colon == std::string_view::npos || colon == 0 || colon + 1 == token.size()) {
            error = "step must use actions:polls";
            return std::nullopt;
        }
        const std::string_view actions = trim(token.substr(0, colon));
        const std::string_view polls_text = trim(token.substr(colon + 1));
        std::uint32_t polls = 0;
        const auto result = std::from_chars(
            polls_text.data(), polls_text.data() + polls_text.size(), polls);
        if (result.ec != std::errc{} || result.ptr != polls_text.data() + polls_text.size()
            || polls == 0 || polls > kMaximumStepPolls) {
            error = "poll count must be an integer from 1 to 1000000";
            return std::nullopt;
        }

        ReplayFrame frame{};
        if (actions != "wait" && actions != "neutral") {
            std::size_t action_cursor = 0;
            while (action_cursor <= actions.size()) {
                const std::size_t plus = actions.find('+', action_cursor);
                const std::size_t action_end =
                    plus == std::string_view::npos ? actions.size() : plus;
                const std::string_view action = trim(
                    actions.substr(action_cursor, action_end - action_cursor));
                if (action.empty() || !add_action(action, frame, error)) {
                    if (error.empty()) error = "step contains an empty action";
                    return std::nullopt;
                }
                if (plus == std::string_view::npos) break;
                action_cursor = plus + 1;
            }
        }

        total_polls += polls;
        if (total_polls > kMaximumTotalPolls) {
            error = "route exceeds 10000000 total polls";
            return std::nullopt;
        }
        steps.push_back({frame, polls});
        if (comma == std::string_view::npos) break;
        cursor = comma + 1;
    }
    return TestInputReplay(std::move(steps), total_polls);
}

ReplayFrame TestInputReplay::next() {
    if (step_index_ >= steps_.size()) {
        return {};
    }
    const ReplayFrame result = steps_[step_index_].frame;
    if (--polls_remaining_ == 0) {
        ++step_index_;
        if (step_index_ < steps_.size()) {
            polls_remaining_ = steps_[step_index_].polls;
        } else {
            completed_pending_ = true;
        }
    }
    return result;
}

bool TestInputReplay::consume_completed() {
    const bool result = completed_pending_;
    completed_pending_ = false;
    return result;
}

std::size_t TestInputReplay::step_count() const {
    return steps_.size();
}

std::uint64_t TestInputReplay::total_polls() const {
    return total_polls_;
}

} // namespace snappad::testing
