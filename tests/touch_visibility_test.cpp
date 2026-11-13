#include "touch_visibility.h"

#include <cstdio>

namespace {

int failures = 0;

void expect(bool condition, const char* step) {
    if (!condition) {
        std::fprintf(stderr, "touch visibility FAIL: %s\n", step);
        ++failures;
    }
}

SnapPadTouchVisibility firstLaunch(bool controllerReady) {
    SnapPadTouchVisibility visibility;
    visibility.autoHide = SnapPadSavedAutoHide(false, false);
    visibility.controllerReady = controllerReady;
    return visibility;
}

} // namespace

int main() {
    expect(!firstLaunch(true).gameplayVisible(), "controller before launch hides by default");
    expect(firstLaunch(false).gameplayVisible(), "no controller keeps touch visible");

    SnapPadTouchVisibility saved;
    saved.autoHide = SnapPadSavedAutoHide(true, false);
    saved.controllerReady = true;
    expect(saved.gameplayVisible(), "saved opt-out survives relaunch");
    expect(SnapPadSavedAutoHide(true, true), "saved opt-in survives relaunch");

    SnapPadTouchVisibility live = firstLaunch(false);
    live.controllerReady = true;
    expect(!live.gameplayVisible(), "connect hides");
    live.controllerReady = false;
    expect(live.gameplayVisible(), "disconnect of Player 1's controller restores");

    SnapPadTouchVisibility preference = firstLaunch(true);
    preference.autoHide = false;
    expect(preference.gameplayVisible(), "auto-hide off restores while connected");
    preference.autoHide = true;
    expect(!preference.gameplayVisible(), "auto-hide on hides while connected");

    SnapPadTouchVisibility show = firstLaunch(true);
    show.enabled = false;
    show.show();
    expect(show.gameplayVisible(), "Show restores with the controller connected");
    expect(show.enabled && !show.autoHide, "Show clears manual hide and turns auto-hide off");

    SnapPadTouchVisibility manual = firstLaunch(false);
    manual.enabled = false;
    expect(!manual.gameplayVisible(), "manual hide holds without a controller");
    manual.show();
    expect(manual.gameplayVisible(), "Show recovers a manual hide");

    if (failures != 0) return 1;
    std::printf("touch visibility policy: pass\n");
    return 0;
}
