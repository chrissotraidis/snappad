#!/usr/bin/env bash
# Verify a private AOT Simulator bundle without launching a Simulator.
set -euo pipefail
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
source "$script_dir/lib/common.sh"

app=${1:?usage: scripts/audit-ios-simulator-bundle.sh <SnapPad.app>}
[[ "$app" = /* ]] || app="$SNAPPAD_ROOT/$app"
binary="$app/SnapPad"
info="$app/Info.plist"
[[ -d "$app" && -x "$binary" && -f "$info" ]] || \
    die "incomplete SnapPad Simulator bundle: $app"

plist_value() { /usr/libexec/PlistBuddy -c "Print :$1" "$info"; }
[[ "$(plist_value CFBundleIdentifier)" == "com.chrissotraidis.snappad" ]] || \
    die "unexpected Simulator bundle identifier"
[[ "$(plist_value CFBundleExecutable)" == "SnapPad" ]] || \
    die "unexpected Simulator bundle executable"
[[ "$(plist_value MinimumOSVersion)" == "15.0" ]] || \
    die "unexpected Simulator minimum OS"
[[ "$(lipo -archs "$binary")" == "arm64" ]] || \
    die "Simulator executable is not arm64-only"
xcrun vtool -show-build "$binary" | rg -q 'platform +IOSSIMULATOR$' || \
    die "bundle executable is not an iOS Simulator product"
xcrun vtool -show-build "$binary" | rg -q 'minos +15\.0$' || \
    die "Simulator executable minimum OS is not iOS 15.0"
[[ -f "$app/PrivacyInfo.xcprivacy" ]] || die "privacy manifest missing"
plutil -lint "$app/PrivacyInfo.xcprivacy" >/dev/null || die "privacy manifest is invalid"

unexpected_runtime=$(otool -L "$binary" | awk 'NR > 1 { print $1 }' | \
    rg -v '^(/System/Library/|/usr/lib/)' || true)
[[ -z "$unexpected_runtime" ]] || \
    die "Simulator app has an unbundled runtime dependency: $unexpected_runtime"
forbidden=$(find "$app" -type f | \
    grep -Ei '\.(z64|v64|n64|rom|elf|map|sav|srm|fla|mobileprovision|p12|p8|pem|key)$' || true)
[[ -z "$forbidden" ]] || \
    die "private/game/signing input found in Simulator app: $forbidden"
personal_path='/''Users/|/Volumes/|/private/var/''folders/'
if LC_ALL=C strings -a "$binary" | \
    grep -Eq "$personal_path|github_pat_|gh[pousr]_|AKIA[0-9A-Z]{16}"; then
    die "Simulator executable contains a personal path or likely credential"
fi

note "AOT arm64 iOS Simulator bundle audit passed (not launched)."
