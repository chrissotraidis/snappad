#!/usr/bin/env bash
# Audit, install in place, and launch a signed private SnapPad device app.
set -euo pipefail
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
source "$script_dir/lib/common.sh"

device=
app="$SNAPPAD_ROOT/build-ios-device/Release-iphoneos/SnapPad.app"
launch=1
while (($#)); do
    case "$1" in
        --device)
            (($# >= 2)) || die "--device requires a CoreDevice identifier or name"
            device=$2
            shift 2
            ;;
        --app)
            (($# >= 2)) || die "--app requires a path to SnapPad.app"
            app=$2
            shift 2
            ;;
        --no-launch)
            launch=0
            shift
            ;;
        *)
            die "usage: scripts/deploy-ios-device.sh --device ID [--app SnapPad.app] [--no-launch]"
            ;;
    esac
done

[[ -n "$device" ]] || \
    die "--device is required; run scripts/check-ios-device-readiness.sh to list paired devices"
[[ "$app" = /* ]] || app="$SNAPPAD_ROOT/$app"
[[ -d "$app" ]] || die "signed SnapPad app not found: $app"

"$script_dir/check-ios-device-readiness.sh"
"$script_dir/audit-ios-device-bundle.sh" "$app"
[[ -d "$app/_CodeSignature" && -f "$app/embedded.mobileprovision" ]] || \
    die "device deployment requires a development-signed app with an embedded profile"
codesign --verify --strict "$app"

booted=$(xcrun simctl list devices | rg '\(Booted\)' || true)
[[ -z "$booted" ]] || \
    die "shut down the booted Simulator before physical-device acceptance: $booted"

binary="$app/SnapPad"
binary_sha256=$(shasum -a 256 "$binary" | awk '{print $1}')
note "Installing in place; SnapPad's existing device data container will not be removed."
note "Candidate executable SHA-256: $binary_sha256"
xcrun devicectl device install app --device "$device" "$app"

if ((launch)); then
    xcrun devicectl device process launch --terminate-existing \
        --device "$device" com.chrissotraidis.snappad
    note "SnapPad launched on $device. Build/install/launch are deployment evidence only; complete the hands-on P3 checklist."
else
    note "SnapPad installed on $device without launching."
fi
