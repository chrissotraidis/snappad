#!/usr/bin/env bash
# Build the exact XXH3 helper used by N64ModernRuntime's ROM validator.
set -euo pipefail
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
source "$script_dir/lib/common.sh"

require_command cc
runtime="$SNAPPAD_REF/paper-mario-recut/lib/N64ModernRuntime"
xxhash="$runtime/thirdparty/xxHash"
source_file="$SNAPPAD_ROOT/tools/rom_xxh3.c"
output_dir="$SNAPPAD_ROOT/build-host-tools"
output="$output_dir/snappad_rom_xxh3"

[[ -f "$xxhash/xxhash.c" && -f "$xxhash/xxhash.h" ]] || \
    die "pinned runtime xxHash source is missing"
mkdir -p "$output_dir"
cc -std=c17 -O2 -Wall -Wextra -Werror \
    -I"$xxhash" "$source_file" "$xxhash/xxhash.c" -o "$output"
[[ -x "$output" ]] || die "ROM XXH3 helper was not produced"
note "ROM XXH3 helper ready: build-host-tools/snappad_rom_xxh3"
