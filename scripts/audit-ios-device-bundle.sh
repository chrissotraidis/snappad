#!/usr/bin/env bash
# Verify a private arm64 iPhoneOS bundle without installing or launching it.
set -euo pipefail
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
source "$script_dir/lib/common.sh"

app=${1:?usage: scripts/audit-ios-device-bundle.sh <SnapPad.app>}
[[ "$app" = /* ]] || app="$SNAPPAD_ROOT/$app"
binary="$app/SnapPad"
info="$app/Info.plist"
[[ -d "$app" && -x "$binary" && -f "$info" ]] || \
    die "incomplete SnapPad iPhoneOS bundle: $app"

plist_value() { /usr/libexec/PlistBuddy -c "Print :$1" "$info"; }
[[ "$(plist_value CFBundleIdentifier)" == "com.chrissotraidis.snappad" ]] || \
    die "unexpected iPhoneOS bundle identifier"
[[ "$(plist_value CFBundleExecutable)" == "SnapPad" ]] || \
    die "unexpected iPhoneOS bundle executable"
[[ "$(plist_value MinimumOSVersion)" == "15.0" ]] || \
    die "unexpected iPhoneOS minimum OS"
[[ "$(lipo -archs "$binary")" == "arm64" ]] || \
    die "iPhoneOS executable is not arm64-only"
xcrun vtool -show-build "$binary" | rg -q 'platform +IOS$' || \
    die "bundle executable is not an iPhoneOS product"
xcrun vtool -show-build "$binary" | rg -q 'minos +15\.0$' || \
    die "iPhoneOS executable minimum OS is not iOS 15.0"
[[ -f "$app/PrivacyInfo.xcprivacy" ]] || die "privacy manifest missing"
plutil -lint "$app/PrivacyInfo.xcprivacy" >/dev/null || \
    die "privacy manifest is invalid"

unexpected_runtime=$(otool -L "$binary" | awk 'NR > 1 { print $1 }' | \
    rg -v '^(/System/Library/|/usr/lib/)' || true)
[[ -z "$unexpected_runtime" ]] || \
    die "iPhoneOS app has an unbundled runtime dependency: $unexpected_runtime"
forbidden=$(find "$app" -type f | \
    grep -Ei '\.(z64|v64|n64|rom|elf|map|sav|srm|fla|p12|p8|pem|key)$' || true)
[[ -z "$forbidden" ]] || \
    die "private game data, a save, or signing secret found in iPhoneOS app: $forbidden"
personal_path='/''Users/|/Volumes/|/private/var/''folders/'
if LC_ALL=C strings -a "$binary" | \
    grep -Eq "$personal_path|github_pat_|gh[pousr]_|AKIA[0-9A-Z]{16}"; then
    die "iPhoneOS executable contains a personal path or likely credential"
fi

if [[ -d "$app/_CodeSignature" || -f "$app/embedded.mobileprovision" ]]; then
    codesign --verify --strict "$app" >/dev/null 2>&1 || \
        die "signed iPhoneOS bundle fails strict code-signature verification"
    note "Private arm64 iPhoneOS bundle audit passed (development signed; not installed)."
else
    if otool -l "$binary" | rg -q 'cmd LC_CODE_SIGNATURE'; then
        die "unsigned iPhoneOS bundle retains a code-signature load command"
    fi
    note "Private arm64 iPhoneOS bundle audit passed (unsigned; not installable yet)."
fi
