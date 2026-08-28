#!/usr/bin/env bash
# Build the ROM-free PaperPad-derived setup/menu/touch shell without game code.
set -euo pipefail
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
source "$script_dir/lib/common.sh"

"$script_dir/check-prerequisites.sh"
"$script_dir/verify-sources.sh"
"$script_dir/check-apple-shell-syntax.sh"

cmake -S "$SNAPPAD_ROOT" -B "$SNAPPAD_ROOT/build-ios-shell" -G Xcode \
    -DCMAKE_SYSTEM_NAME=iOS \
    -DCMAKE_OSX_SYSROOT=iphonesimulator \
    -DCMAKE_OSX_ARCHITECTURES=arm64 \
    -DSNAPPAD_BUILD_SHELL_PREVIEW=ON \
    -DBUILD_TESTING=OFF
cmake --build "$SNAPPAD_ROOT/build-ios-shell" --config Release --target SnapPadShell -- \
    -sdk iphonesimulator CODE_SIGNING_ALLOWED=NO

app="$SNAPPAD_ROOT/build-ios-shell/Release-iphonesimulator/SnapPad.app"
[[ -d "$app" ]] || die "shell app missing: $app"
note "ROM-free shell preview built at build-ios-shell/Release-iphonesimulator/SnapPad.app"
