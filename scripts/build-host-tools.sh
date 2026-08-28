#!/usr/bin/env bash
# Build N64Recomp and RSPRecomp host tools from the exact patched ReCut pin.
set -euo pipefail
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
source "$script_dir/lib/common.sh"

"$script_dir/check-prerequisites.sh"
"$script_dir/verify-sources.sh"
"$script_dir/apply-patches.sh"

n64recomp="$SNAPPAD_REF/paper-mario-recut/lib/N64ModernRuntime/N64Recomp"
build_dir="$SNAPPAD_ROOT/build-host-tools"
for dependency in lib/rabbitizer lib/ELFIO lib/fmt lib/tomlplusplus lib/sljit; do
    [[ -d "$n64recomp/$dependency" ]] || die "N64Recomp dependency missing: $dependency"
done

cmake -S "$n64recomp" -B "$build_dir" -G Ninja -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_CXX_FLAGS="-DFMT_USE_CONSTEVAL=0"
build_jobs=$(configured_build_jobs)
if [[ -n "$build_jobs" ]]; then
    cmake --build "$build_dir" --parallel "$build_jobs" --target N64Recomp RSPRecomp
else
    cmake --build "$build_dir" --parallel --target N64Recomp RSPRecomp
fi

for tool in N64Recomp RSPRecomp; do
    [[ -x "$build_dir/$tool" ]] || die "host tool was not produced: $tool"
done
"$script_dir/build-rom-hash-tool.sh"
note "Host tools ready: build-host-tools/N64Recomp and build-host-tools/RSPRecomp"
