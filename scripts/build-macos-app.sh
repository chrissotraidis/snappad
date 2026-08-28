#!/usr/bin/env bash
# Link the exact generated Pokemon Snap core into the private native macOS app.
set -euo pipefail
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
source "$script_dir/lib/common.sh"

"$script_dir/check-prerequisites.sh"
"$script_dir/verify-sources.sh"
"$script_dir/apply-patches.sh"

metadata="$SNAPPAD_GENERATED/aot/snappad_game_metadata.h"
lookup="$SNAPPAD_GENERATED/aot/snappad_recomp_out/lookup.cpp"
rsp="$SNAPPAD_GENERATED/aot/rsp/aspMain.cpp"
for input in "$metadata" "$lookup" "$rsp"; do
    [[ -s "$input" ]] || \
        die "verified generated app input missing: $input; complete G1 and scripts/generate-game.sh"
done
"$script_dir/verify-generated-evidence.py"

build_dir="$SNAPPAD_ROOT/build-macos-app"
jobs=${SNAPPAD_BUILD_JOBS:-6}
cmake -S "$SNAPPAD_ROOT" -B "$build_dir" -G Ninja \
    -DBUILD_TESTING=OFF \
    -DSNAPPAD_BUILD_NATIVE_APP=ON \
    -DCMAKE_BUILD_TYPE=Release
cmake --build "$build_dir" --target SnapPad --parallel "$jobs"
app="$build_dir/SnapPad.app"
[[ -x "$app/Contents/MacOS/SnapPad" ]] || die "native SnapPad app bundle is incomplete: $app"
"$script_dir/audit-macos-app.sh" "$app"
note "Private native macOS app linked: $app"
