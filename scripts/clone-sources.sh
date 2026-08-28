#!/usr/bin/env bash
set -euo pipefail
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
source "$script_dir/lib/common.sh"

require_command git
require_command jq
mkdir -p "$SNAPPAD_REF"

clone_locked_source pokemonSnap "$SNAPPAD_REF/pokemonsnap" "Pokemon Snap decomp"
clone_locked_source paperpadReference "$SNAPPAD_REF/paperpad" "PaperPad reference"
clone_locked_source paperMarioReCut "$SNAPPAD_REF/paper-mario-recut" "Paper-Mario-ReCut"
clone_locked_source mupen64plusRspHle "$SNAPPAD_REF/mupen64plus-rsp-hle" "mupen64plus-rsp-hle"
clone_locked_source sdl2 "$SNAPPAD_REF/SDL2" "SDL2"
clone_locked_source zstd "$SNAPPAD_REF/zstd" "zstd"

# ReCut vendors DXC as an ordinary binary blob; some checkout/archive paths
# lose the executable bit required by RT64's native shader build.
for dxc in "$SNAPPAD_REF/paper-mario-recut/lib/rt64/src/contrib/dxc/bin/"*/dxc-macos; do
    [[ -f "$dxc" ]] && chmod +x "$dxc"
done

note "Pinned SnapPad sources are ready and push-disabled."
