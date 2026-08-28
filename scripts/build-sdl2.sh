#!/usr/bin/env bash
# Build the pinned native SDL2 static library used by the macOS target.
set -euo pipefail
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
source "$script_dir/lib/common.sh"

source_dir="$SNAPPAD_REF/SDL2"
build_dir="$SNAPPAD_ROOT/build-macos-sdl2"
[[ -d "$source_dir/.git" ]] || die "SDL2 is missing; run scripts/clone-sources.sh"
prefix_flags="-ffile-prefix-map=$SNAPPAD_ROOT=. -fmacro-prefix-map=$SNAPPAD_ROOT=. -fdebug-prefix-map=$SNAPPAD_ROOT=."

cmake -S "$source_dir" -B "$build_dir" -G Ninja \
    -DSDL_STATIC=ON -DSDL_SHARED=OFF -DSDL_TEST=OFF -DSDL_TESTS=OFF \
    -DCMAKE_C_FLAGS="$prefix_flags" \
    -DCMAKE_CXX_FLAGS="$prefix_flags" \
    -DCMAKE_BUILD_TYPE=Release
build_jobs=$(configured_build_jobs)
if [[ -n "$build_jobs" ]]; then
    cmake --build "$build_dir" --parallel "$build_jobs" --target SDL2-static
else
    cmake --build "$build_dir" --parallel --target SDL2-static
fi
[[ -f "$build_dir/libSDL2.a" ]] || die "SDL2 static library was not produced"
note "Native SDL2 ready: $build_dir/libSDL2.a"
