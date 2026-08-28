#!/usr/bin/env bash
set -euo pipefail
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
source "$script_dir/lib/common.sh"

require_command git
require_command jq

verify_one() {
    local key=$1
    local path=$2
    local label=$3
    assert_revision "$path" "$(lock_value "$key" commit)" "$label"
    local allow_patches=${4:-false}
    if [[ "$allow_patches" != true ]]; then
        assert_clean "$path" "$label"
    fi
    local push_url
    push_url=$(git -C "$path" remote get-url --push origin 2>/dev/null || true)
    [[ "$push_url" == "DISABLED" ]] || die "$label push URL is not disabled"
}

verify_one pokemonSnap "$SNAPPAD_REF/pokemonsnap" "Pokemon Snap decomp"
verify_one paperpadReference "$SNAPPAD_REF/paperpad" "PaperPad reference"

for key_path_label in \
    "paperMarioReCut|$SNAPPAD_REF/paper-mario-recut|Paper-Mario-ReCut" \
    "mupen64plusRspHle|$SNAPPAD_REF/mupen64plus-rsp-hle|mupen64plus-rsp-hle" \
    "sdl2|$SNAPPAD_REF/SDL2|SDL2" \
    "zstd|$SNAPPAD_REF/zstd|zstd"; do
    IFS='|' read -r key path label <<< "$key_path_label"
    if [[ -d "$path/.git" ]]; then
        if [[ "$key" == "paperMarioReCut" ]]; then
            verify_one "$key" "$path" "$label" true
        else
            verify_one "$key" "$path" "$label"
        fi
    else
        note "$label not cloned yet (run scripts/clone-sources.sh before G2)."
    fi
done

note "Present pinned sources verified."
