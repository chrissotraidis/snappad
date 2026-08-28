#!/usr/bin/env bash
set -euo pipefail
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
source "$script_dir/lib/common.sh"

sdk_path=$(xcrun --sdk iphonesimulator --show-sdk-path)
for source in \
    port/apple/ios_main.mm \
    port/apple/rom_setup.mm \
    port/apple/diagnostics.mm \
    port/apple/snappad_paths.mm; do
    xcrun --sdk iphonesimulator clang++ -fsyntax-only -fblocks -std=c++20 \
        -target arm64-apple-ios15.0-simulator -isysroot "$sdk_path" \
        -Iport/apple -Iport/runtime -Iref/SDL2/include "$source"
done
note "SnapPad Apple shell syntax passed for arm64 iOS Simulator."
