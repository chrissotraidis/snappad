#!/usr/bin/env bash
# PadMint's iPhone/iPad build of SnapPad, from a fresh clone: pinned ROM-free
# sources, your own Pokémon Snap (USA) ROM checked and decompiled privately,
# the ahead-of-time game core, the unsigned device app and an IPA to sign with
# your own Apple ID. The ROM stays on this Mac; the IPA holds code made from it,
# so keep your copy to yourself.
#
#   scripts/build-padmint-ios.sh ROM OUTPUT.ipa
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
rom="${1:?usage: scripts/build-padmint-ios.sh ROM OUTPUT.ipa}"
output="${2:?usage: scripts/build-padmint-ios.sh ROM OUTPUT.ipa}"
cd "$root"

scripts/check-prerequisites.sh
echo "SnapPad: fetching the pinned sources"
scripts/clone-sources.sh
scripts/verify-sources.sh
echo "SnapPad: checking and decompiling your ROM"
scripts/build-decomp.sh --rom "$rom"
echo "SnapPad: generating the game core"
scripts/generate-game.sh
echo "SnapPad: building the iPhone/iPad app"
scripts/build-ios-device.sh --unsigned
echo "SnapPad: packaging"
scripts/package-unsigned-ipa.sh "$root/build-ios-device/Release-iphoneos/SnapPad.app" "$output"

