#pragma once

#include <array>
#include <atomic>
#include <cstddef>
#include <cstdint>

// Ported directly from PaperPad's proven touch edge/latch mechanism. A quick
// tap remains visible for a bounded number of runtime polls, while clearAll()
// guarantees native UI and lifecycle transitions cannot leave held input.
class SnapPadTouchTapLatch {
public:
    void extend(uint16_t mask, uint8_t polls) {
        for (std::size_t bit = 0; bit < counters_.size(); ++bit) {
            const uint16_t bitMask = static_cast<uint16_t>(1u << bit);
            if ((mask & bitMask) == 0) continue;
            uint8_t current = counters_[bit].load(std::memory_order_relaxed);
            while (current < polls &&
                   !counters_[bit].compare_exchange_weak(
                       current, polls, std::memory_order_relaxed)) {}
        }
    }

    void clear(uint16_t mask) {
        for (std::size_t bit = 0; bit < counters_.size(); ++bit) {
            if ((mask & static_cast<uint16_t>(1u << bit)) != 0) {
                counters_[bit].store(0, std::memory_order_relaxed);
            }
        }
    }

    void clearAll() {
        for (auto& counter : counters_) {
            counter.store(0, std::memory_order_relaxed);
        }
    }

    uint16_t consume() {
        uint16_t buttons = 0;
        for (std::size_t bit = 0; bit < counters_.size(); ++bit) {
            uint8_t current = counters_[bit].load(std::memory_order_relaxed);
            while (current != 0) {
                if (counters_[bit].compare_exchange_weak(
                        current, static_cast<uint8_t>(current - 1),
                        std::memory_order_relaxed)) {
                    buttons |= static_cast<uint16_t>(1u << bit);
                    break;
                }
            }
        }
        return buttons;
    }

private:
    std::array<std::atomic<uint8_t>, 16> counters_{};
};
