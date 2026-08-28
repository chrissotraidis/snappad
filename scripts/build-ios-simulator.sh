#!/usr/bin/env bash
# Build the verified AOT core as a ROM-free arm64 iPad/iPhone Simulator app.
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
        die "verified generated Simulator input missing: $input; complete G1 and scripts/generate-game.sh"
done
"$script_dir/verify-generated-evidence.py"
"$script_dir/build-rt64-host-tools.sh"

build_dir="$SNAPPAD_ROOT/build-ios-simulator"
cmake -S "$SNAPPAD_ROOT" -B "$build_dir" -G Xcode \
    -DBUILD_TESTING=OFF \
    -DSNAPPAD_BUILD_NATIVE_APP=ON \
    -DCMAKE_SYSTEM_NAME=iOS \
    -DCMAKE_OSX_SYSROOT=iphonesimulator \
    -DCMAKE_OSX_ARCHITECTURES=arm64 \
    -DCMAKE_XCODE_ATTRIBUTE_CODE_SIGNING_ALLOWED=NO
cmake --build "$build_dir" --config Release --target SnapPad -- \
    -sdk iphonesimulator CODE_SIGNING_ALLOWED=NO

app="$build_dir/Release-iphonesimulator/SnapPad.app"
[[ -d "$app" ]] || app="$build_dir/Release/SnapPad.app"
[[ -d "$app" ]] || die "SnapPad Simulator app was not produced"
"$script_dir/audit-ios-simulator-bundle.sh" "$app"
note "Private AOT iOS Simulator app ready: $app"
