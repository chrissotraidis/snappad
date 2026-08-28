#!/usr/bin/env bash
# Package the audited unsigned iPhoneOS app and dependency notices as an IPA.
set -euo pipefail
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
source "$script_dir/lib/common.sh"

app=${1:-$SNAPPAD_ROOT/build-ios-device/Release-iphoneos/SnapPad.app}
[[ "$app" = /* ]] || app="$SNAPPAD_ROOT/$app"
[[ -d "$app" ]] || die "unsigned SnapPad app not found: $app"
"$script_dir/audit-ios-device-bundle.sh" "$app"
[[ ! -d "$app/_CodeSignature" && ! -f "$app/embedded.mobileprovision" ]] || \
    die "refusing to publish an app containing signing material"

version=$(/usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' "$app/Info.plist")
output=${2:-$SNAPPAD_ROOT/artifacts/SnapPad-v${version}-unsigned.ipa}
[[ "$output" = /* ]] || output="$SNAPPAD_ROOT/$output"
mkdir -p "$(dirname -- "$output")"

package_root=$(mktemp -d /tmp/snappad-ipa-package.XXXXXX)
trap 'rm -rf "$package_root"' EXIT
mkdir -p "$package_root/Payload" "$package_root/ThirdPartyLicenses"
ditto "$app" "$package_root/Payload/SnapPad.app"
ditto "$SNAPPAD_ROOT/RIGHTS_AND_LICENSES.md" "$package_root/RIGHTS_AND_LICENSES.md"

license_count=0
while IFS= read -r -d '' license_file; do
    relative=${license_file#"$SNAPPAD_ROOT/"}
    destination="$package_root/ThirdPartyLicenses/$relative"
    mkdir -p "$(dirname -- "$destination")"
    ditto "$license_file" "$destination"
    license_count=$((license_count + 1))
done < <(
    find "$SNAPPAD_ROOT/ref/SDL2" \
         "$SNAPPAD_ROOT/ref/paper-mario-recut/lib/N64ModernRuntime" \
         "$SNAPPAD_ROOT/ref/paper-mario-recut/lib/rt64" \
         "$SNAPPAD_ROOT/ref/zstd" \
         -type f \( -iname 'LICENSE' -o -iname 'LICENSE.*' \
                    -o -iname 'COPYING' -o -iname 'COPYING.*' \
                    -o -iname 'NOTICE' -o -iname 'NOTICE.*' \) \
         -print0 | sort -z
)
((license_count > 0)) || die "no dependency license files were found"

# Fixed mtimes plus sorted input keep repeated packages byte-identical.
find "$package_root" -exec touch -h -t 202608280000 {} +
rm -f "$output" "$output.sha256"
(
    cd "$package_root"
    find Payload RIGHTS_AND_LICENSES.md ThirdPartyLicenses -print | \
        LC_ALL=C sort | zip -X -q "$output" -@
)

"$script_dir/audit-ios-package.sh" "$output"
(
    cd "$(dirname -- "$output")"
    shasum -a 256 "$(basename -- "$output")" > "$(basename -- "$output").sha256"
)
note "Packaged unsigned SnapPad IPA: $output"
note "Third-party notice files: $license_count"
