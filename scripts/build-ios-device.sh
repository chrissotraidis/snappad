#!/usr/bin/env bash
# Build the verified AOT core as a private arm64 iPad/iPhone device app.
set -euo pipefail
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
source "$script_dir/lib/common.sh"

mode=auto
while (($#)); do
    case "$1" in
        --signed) mode=signed; shift ;;
        --unsigned) mode=unsigned; shift ;;
        *) die "usage: scripts/build-ios-device.sh [--signed|--unsigned]" ;;
    esac
done

"$script_dir/check-prerequisites.sh"
"$script_dir/verify-sources.sh"
"$script_dir/apply-patches.sh"

metadata="$SNAPPAD_GENERATED/aot/snappad_game_metadata.h"
lookup="$SNAPPAD_GENERATED/aot/snappad_recomp_out/lookup.cpp"
rsp="$SNAPPAD_GENERATED/aot/rsp/aspMain.cpp"
for input in "$metadata" "$lookup" "$rsp"; do
    [[ -s "$input" ]] || \
        die "verified generated device input missing: $input; complete G1 and scripts/generate-game.sh"
done
"$script_dir/verify-generated-evidence.py"
"$script_dir/build-rt64-host-tools.sh"

team_id=${SNAPPAD_APPLE_TEAM_ID:-}
if [[ "$mode" == auto ]]; then
    [[ -n "$team_id" ]] && mode=signed || mode=unsigned
fi
if [[ "$mode" == signed && -z "$team_id" ]]; then
    die "--signed requires SNAPPAD_APPLE_TEAM_ID to name your Apple development team"
fi

build_dir="$SNAPPAD_ROOT/build-ios-device"
configure=(
    cmake -S "$SNAPPAD_ROOT" -B "$build_dir" -G Xcode
    -DBUILD_TESTING=OFF
    -DSNAPPAD_BUILD_NATIVE_APP=ON
    -DCMAKE_SYSTEM_NAME=iOS
    -DCMAKE_OSX_SYSROOT=iphoneos
    -DCMAKE_OSX_ARCHITECTURES=arm64
)
build=(
    cmake --build "$build_dir" --config Release --target SnapPad --
    -sdk iphoneos
)
if [[ "$mode" == signed ]]; then
    configure+=("-DDEVELOPMENT_TEAM=$team_id")
    build+=(CODE_SIGN_STYLE=Automatic "DEVELOPMENT_TEAM=$team_id" \
        "CODE_SIGN_IDENTITY=Apple Development")
else
    configure+=(-DCMAKE_XCODE_ATTRIBUTE_CODE_SIGNING_ALLOWED=NO)
    build+=(CODE_SIGNING_ALLOWED=NO)
fi

"${configure[@]}"
"${build[@]}"

app="$build_dir/Release-iphoneos/SnapPad.app"
[[ -d "$app" ]] || app="$build_dir/Release/SnapPad.app"
[[ -d "$app" ]] || die "SnapPad iPhoneOS app was not produced"
"$script_dir/audit-ios-device-bundle.sh" "$app"
if [[ "$mode" == signed ]]; then
    note "Private signed iPad/iPhone app ready: $app"
else
    note "Private unsigned iPad/iPhone app ready: $app"
    note "Set SNAPPAD_APPLE_TEAM_ID and rerun with --signed before device installation."
fi
