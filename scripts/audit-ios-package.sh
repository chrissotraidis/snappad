#!/usr/bin/env bash
# Fail closed when auditing a public unsigned SnapPad IPA.
set -euo pipefail
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
source "$script_dir/lib/common.sh"

ipa=${1:?usage: scripts/audit-ios-package.sh <SnapPad.ipa>}
[[ "$ipa" = /* ]] || ipa="$SNAPPAD_ROOT/$ipa"
[[ -f "$ipa" ]] || die "SnapPad IPA not found: $ipa"

unzip -tq "$ipa" >/dev/null || die "IPA ZIP integrity check failed"
entries=$(unzip -Z1 "$ipa")
printf '%s\n' "$entries" | grep -Fxq 'Payload/SnapPad.app/SnapPad' || \
    die "IPA does not contain the SnapPad executable"
printf '%s\n' "$entries" | grep -Fxq 'RIGHTS_AND_LICENSES.md' || \
    die "IPA rights notice is missing"
printf '%s\n' "$entries" | grep -Fq 'ThirdPartyLicenses/' || \
    die "IPA third-party licenses are missing"
if printf '%s\n' "$entries" | grep -Eq '(^|/)__MACOSX/|(^|/)\.DS_Store$'; then
    die "IPA contains macOS metadata"
fi
if printf '%s\n' "$entries" | grep -Eiq \
    '\.(z64|v64|n64|rom|elf|map|sav|srm|fla|p12|p8|pem|key|mobileprovision|provisionprofile)$'; then
    die "IPA contains private game data, generated input, or signing material"
fi

extract_root=$(mktemp -d /tmp/snappad-ipa-audit.XXXXXX)
trap 'rm -rf "$extract_root"' EXIT
unzip -qq "$ipa" -d "$extract_root"
app="$extract_root/Payload/SnapPad.app"
"$script_dir/audit-ios-device-bundle.sh" "$app"
[[ ! -d "$app/_CodeSignature" && ! -f "$app/embedded.mobileprovision" ]] || \
    die "public IPA must not contain a signature or provisioning profile"
if codesign --verify --strict "$app" >/dev/null 2>&1; then
    die "public IPA unexpectedly contains a valid code signature"
fi

version=$(/usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' "$app/Info.plist")
build=$(/usr/libexec/PlistBuddy -c 'Print :CFBundleVersion' "$app/Info.plist")
[[ "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || die "invalid IPA version: $version"
[[ "$build" =~ ^[1-9][0-9]*$ ]] || die "invalid IPA build number: $build"

note "Public unsigned SnapPad IPA audit passed: v$version ($build)"
note "SHA-256: $(shasum -a 256 "$ipa" | awk '{print $1}')"
