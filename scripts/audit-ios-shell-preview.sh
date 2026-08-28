#!/usr/bin/env bash
set -euo pipefail
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
source "$script_dir/lib/common.sh"

app="$SNAPPAD_ROOT/build-ios-shell/Release-iphonesimulator/SnapPad.app"
binary="$app/SnapPad"
[[ -d "$app" && -f "$binary" ]] || die "build the shell preview first"

bundle_id=$(/usr/libexec/PlistBuddy -c 'Print :CFBundleIdentifier' "$app/Info.plist")
[[ "$bundle_id" == "com.chrissotraidis.snappad" ]] || die "unexpected bundle ID: $bundle_id"
file "$binary" | rg -q 'Mach-O 64-bit executable arm64' || die "shell preview is not arm64"
[[ -f "$app/PrivacyInfo.xcprivacy" ]] || die "privacy manifest missing"

forbidden=$(find "$app" -type f | grep -Ei '\.(z64|v64|n64|rom|elf|sav|srm|fla|mobileprovision|p12|p8|pem|key)$' || true)
[[ -z "$forbidden" ]] || { printf '%s\n' "$forbidden" >&2; die "private/game/signing data found in app"; }

personal_path='/''Users/[^/[:space:]]+|/private/var/''folders/'
if strings "$binary" | grep -Eq "$personal_path"; then
    die "personal build path embedded in shell preview"
fi

note "ROM-free arm64 iOS shell preview audit passed ($bundle_id)."
