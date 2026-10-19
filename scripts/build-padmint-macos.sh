#!/usr/bin/env bash
# PadMint's Mac build of SnapPad, from a fresh clone: pinned ROM-free sources,
# your own Pokémon Snap (USA) ROM checked and decompiled privately, the
# ahead-of-time game core and the native Apple Silicon SnapPad.app, zipped.
# The app holds code made from your ROM, so keep your copy to yourself.
#
#   scripts/build-padmint-macos.sh ROM OUTPUT.zip
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
rom="${1:?usage: scripts/build-padmint-macos.sh ROM OUTPUT.zip}"
output="${2:?usage: scripts/build-padmint-macos.sh ROM OUTPUT.zip}"
cd "$root"

scripts/check-prerequisites.sh
echo "SnapPad: fetching the pinned sources"
scripts/clone-sources.sh
scripts/verify-sources.sh
echo "SnapPad: checking and decompiling your ROM"
scripts/build-decomp.sh --rom "$rom"
echo "SnapPad: building the recompiler host tools"
scripts/build-host-tools.sh
echo "SnapPad: generating the game core"
scripts/generate-game.sh
echo "SnapPad: building the pinned SDL2 for the Mac app"
scripts/build-sdl2.sh
echo "SnapPad: building the Mac app"
scripts/build-macos-app.sh
app="$root/build-macos-app/SnapPad.app"
echo "SnapPad: signing for this Mac and packaging"
codesign --force --deep --sign - "$app"
codesign --verify --deep --strict "$app"
rm -f "$output"
ditto -c -k --keepParent "$app" "$output"
