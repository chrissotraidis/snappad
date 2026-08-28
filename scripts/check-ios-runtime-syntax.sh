#!/usr/bin/env bash
# Compile the real runner/renderer iOS branches without generated game bytes.
set -euo pipefail
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
source "$script_dir/lib/common.sh"

runtime="$SNAPPAD_REF/paper-mario-recut/lib/N64ModernRuntime"
renderer="$SNAPPAD_REF/paper-mario-recut/lib/rt64"
generated_headers="$SNAPPAD_ROOT/build-macos-runtime/rt64/src"
[[ -d "$generated_headers" ]] || \
    die "RT64 generated headers missing; run scripts/build-macos-runtime-stack.sh"

sdk_path=$(xcrun --sdk iphonesimulator --show-sdk-path)
common=(
    -fsyntax-only -fblocks -std=c++20
    -target arm64-apple-ios15.0-simulator -isysroot "$sdk_path"
    -DHLSL_CPU
    -I"$SNAPPAD_ROOT/tests/fixtures"
    -I"$SNAPPAD_ROOT/port/runtime"
    -I"$SNAPPAD_ROOT/port/apple"
    -I"$SNAPPAD_REF/SDL2/include"
    -I"$runtime/ultramodern/include"
    -I"$runtime/librecomp/include"
    -I"$runtime/N64Recomp/include"
    -I"$runtime/thirdparty"
    -I"$runtime/thirdparty/concurrentqueue"
    -I"$runtime/thirdparty/sse2neon"
    -I"$renderer/src/contrib"
    -I"$renderer/src/contrib/hlslpp/include"
    -I"$renderer/src"
    -I"$renderer/src/rhi"
    -I"$renderer/src/render"
    -I"$generated_headers"
)

for source in \
    "$SNAPPAD_ROOT/port/runtime/snappad_runner.cpp" \
    "$SNAPPAD_ROOT/port/runtime/snappad_rt64_context.cpp"; do
    xcrun --sdk iphonesimulator clang++ "${common[@]}" "$source"
done
note "SnapPad runner and RT64 context syntax passed for arm64 iOS Simulator."
