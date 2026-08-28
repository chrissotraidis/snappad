#!/usr/bin/env bash
# Verify the ROM-free native link result is arm64, system-only, and reproducible.
set -euo pipefail
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
source "$script_dir/lib/common.sh"

probe="$SNAPPAD_ROOT/build-macos-runtime/snappad_native_link_probe"
[[ -x "$probe" ]] || die "native link probe missing: $probe"
[[ "$(lipo -archs "$probe")" == "arm64" ]] || \
    die "native link probe is not arm64-only"

non_system=$(otool -L "$probe" | tail -n +2 | awk '{print $1}' | \
    awk '$0 !~ /^\/System\/Library\// && $0 !~ /^\/usr\/lib\// {print}')
[[ -z "$non_system" ]] || die "native link probe has non-system dynamic dependencies: $non_system"
if strings "$probe" | rg -F -q "$SNAPPAD_ROOT"; then
    die "native link probe embeds the local checkout path"
fi
note "Native link probe audit passed (arm64, system-only dylibs, no checkout path)."
