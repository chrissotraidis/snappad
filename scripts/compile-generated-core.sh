#!/usr/bin/env bash
# Compile the verified AOT CPU/RSP output and SnapPad-owned runtime glue.
set -euo pipefail
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
source "$script_dir/lib/common.sh"

"$script_dir/check-prerequisites.sh"
"$script_dir/verify-sources.sh"
"$script_dir/apply-patches.sh"
"$script_dir/verify-generated-evidence.py"

build_dir="$SNAPPAD_ROOT/build-generated-core"
cmake -S "$SNAPPAD_ROOT" -B "$build_dir" -G Ninja \
    -DCMAKE_BUILD_TYPE=RelWithDebInfo \
    -DBUILD_TESTING=OFF \
    -DSNAPPAD_BUILD_GENERATED_CORE=ON

build_jobs=$(configured_build_jobs)
if [[ -n "$build_jobs" ]]; then
    cmake --build "$build_dir" --parallel "$build_jobs" \
        --target snappad_generated_core
else
    cmake --build "$build_dir" --parallel \
        --target snappad_generated_core
fi

[[ -s "$build_dir/libsnappad_recompiled_funcs.a" ]] || \
    die "generated CPU archive missing"
[[ -s "$build_dir/libsnappad_generated_core.a" ]] || \
    die "generated native glue/RSP archive missing"
note "Generated CPU, audio RSP, overlay, and native glue sources compile cleanly."
