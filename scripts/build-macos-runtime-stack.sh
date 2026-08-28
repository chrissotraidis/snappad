#!/usr/bin/env bash
# Compile the patched ROM-free N64ModernRuntime + RT64 Apple stack.
set -euo pipefail
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
source "$script_dir/lib/common.sh"

"$script_dir/check-prerequisites.sh"
"$script_dir/verify-sources.sh"
"$script_dir/apply-patches.sh"
[[ -s "$SNAPPAD_ROOT/build-macos-sdl2/libSDL2.a" ]] || \
    die "pinned native SDL2 archive missing; run scripts/build-sdl2.sh"
dxc="$SNAPPAD_REF/paper-mario-recut/lib/rt64/src/contrib/dxc/bin/arm64/dxc-macos"
[[ -s "$dxc" ]] || die "pinned arm64 DXC binary missing: $dxc"
chmod +x "$dxc"
[[ -x "$dxc" ]] || die "pinned arm64 DXC binary is not executable: $dxc"

build_dir="$SNAPPAD_ROOT/build-macos-runtime"
jobs=${SNAPPAD_BUILD_JOBS:-6}
cmake -S "$SNAPPAD_ROOT" -B "$build_dir" -G Ninja \
    -DBUILD_TESTING=OFF \
    -DSNAPPAD_BUILD_RUNTIME_STACK=ON \
    -DCMAKE_BUILD_TYPE=Release
cmake --build "$build_dir" --target \
    librecomp ultramodern rt64 snappad_runner_syntax \
    snappad_native_link_probe --parallel "$jobs"
for archive in \
    "$build_dir/runtime/librecomp/liblibrecomp.a" \
    "$build_dir/runtime/ultramodern/libultramodern.a" \
    "$build_dir/rt64/rt64.a"; do
    [[ -s "$archive" ]] || die "native runtime archive missing: $archive"
    [[ "$(lipo -archs "$archive")" == "arm64" ]] || \
        die "native runtime archive is not arm64-only: $archive"
done
rg -q -- '-DN64MODERN_NO_DYNAMIC_CODE=1' "$build_dir/compile_commands.json" || \
    die "librecomp was not compiled with runtime dynamic code disabled"
[[ -x "$build_dir/snappad_native_link_probe" ]] || \
    die "ROM-free native runner link probe is missing"
[[ "$(lipo -archs "$build_dir/snappad_native_link_probe")" == "arm64" ]] || \
    die "ROM-free native runner link probe is not arm64-only"
"$script_dir/audit-native-link-probe.sh"
note "ROM-free macOS runtime stack compiled: $build_dir"
