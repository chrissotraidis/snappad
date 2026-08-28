#!/usr/bin/env bash
# Verify downloaded decomp executables before any of them compile game code.
set -euo pipefail
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
source "$script_dir/lib/common.sh"

verify_sha256() {
    path=$1
    expected=$2
    [[ -x "$path" ]] || die "decomp tool missing or not executable: $path"
    actual=$(shasum -a 256 "$path" | awk '{print $1}')
    [[ "$actual" == "$expected" ]] || die "decomp tool hash mismatch: $path"
}

verify_sha256 "$SNAPPAD_REF/pokemonsnap/tools/ido5.3/cc" \
    "$(jq -er '.decomp.toolchain.ido53MacArm64CcSha256' "$SNAPPAD_LOCK")"
verify_sha256 "$SNAPPAD_REF/pokemonsnap/tools/ido7.1/cc" \
    "$(jq -er '.decomp.toolchain.ido71MacArm64CcSha256' "$SNAPPAD_LOCK")"
verify_sha256 "$SNAPPAD_REF/pokemonsnap/tools/asm_proc/asm-processor" \
    "$(jq -er '.decomp.toolchain.asmProcessor101MacArm64Sha256' "$SNAPPAD_LOCK")"

readelf="$SNAPPAD_ROOT/build-tools/mips-binutils-$(jq -er '.decomp.toolchain.mipsBinutils.version' "$SNAPPAD_LOCK")/bin/mips-linux-gnu-readelf"
[[ -x "$readelf" ]] || die "local MIPS readelf missing: $readelf"
"$readelf" --version | head -n 1 | rg -q "$(jq -er '.decomp.toolchain.mipsBinutils.version' "$SNAPPAD_LOCK")" || \
    die "local MIPS readelf version mismatch"

note "Pinned decomp toolchain verified."
