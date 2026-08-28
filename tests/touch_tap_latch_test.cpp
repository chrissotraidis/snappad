#include "touch_tap_latch.h"

#include <cstdio>
#include <cstdlib>

namespace {

[[noreturn]] void fail(const char* message) {
    std::fprintf(stderr, "touch_tap_latch_test: %s\n", message);
    std::exit(EXIT_FAILURE);
}

void require(bool condition, const char* message) {
    if (!condition) fail(message);
}

} // namespace

int main() {
    SnapPadTouchTapLatch latch;
    constexpr uint16_t a = 0x8000;
    constexpr uint16_t b = 0x4000;

    latch.extend(a, 3);
    require(latch.consume() == a, "first poll missed quick tap");
    latch.extend(a, 2);
    require(latch.consume() == a, "extend shortened an active tap");
    require(latch.consume() == a, "third poll missed quick tap");
    require(latch.consume() == 0, "tap remained held beyond its bounded polls");

    latch.extend(a | b, 2);
    latch.clear(a);
    require(latch.consume() == b, "selective clear changed the wrong button");
    latch.clearAll();
    require(latch.consume() == 0, "clearAll left a button logically held");

    // Pokémon Snap's camera path is a true two-finger combination: Z remains
    // held while A is an exactly one-sample action edge. This mirrors the iOS
    // bridge's raw-held | consumed-pulse snapshot without needing synthetic
    // UIKit touch injection.
    constexpr uint16_t z = 0x2000;
    constexpr uint16_t start = 0x1000;
    latch.extend(a, 1);
    require((z | latch.consume()) == (z | a),
        "simultaneous held Z and pulsed A missed the shutter chord");
    require((z | latch.consume()) == z,
        "pulsed A repeated while Z remained held");
    require(latch.consume() == 0,
        "released Z remained in the mixed touch snapshot");

    latch.extend(start, 1);
    require(latch.consume() == start,
        "single-sample Start action edge was not delivered");
    require(latch.consume() == 0,
        "single-sample Start action edge repeated");

    std::puts("touch_tap_latch_test: all scenarios passed");
    return EXIT_SUCCESS;
}
