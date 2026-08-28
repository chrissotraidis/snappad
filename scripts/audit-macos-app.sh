#!/usr/bin/env bash
# Fail closed if the private production bundle is non-native or packages source/ROM inputs.
set -euo pipefail
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
source "$script_dir/lib/common.sh"

app=${1:-"$SNAPPAD_ROOT/build-macos-app/SnapPad.app"}
info="$app/Contents/Info.plist"
binary="$app/Contents/MacOS/SnapPad"

[[ -d "$app" ]] || die "native SnapPad app bundle missing: $app"
[[ -f "$info" ]] || die "native SnapPad Info.plist missing: $info"
[[ -x "$binary" ]] || die "native SnapPad executable missing: $binary"

bundle_id=$(plutil -extract CFBundleIdentifier raw -- "$info")
[[ "$bundle_id" == "com.chrissotraidis.snappad" ]] || \
    die "unexpected native SnapPad bundle identifier: $bundle_id"
bundle_executable=$(plutil -extract CFBundleExecutable raw -- "$info")
[[ "$bundle_executable" == "SnapPad" ]] || \
    die "unexpected native SnapPad bundle executable: $bundle_executable"
[[ "$(lipo -archs "$binary")" == "arm64" ]] || \
    die "native SnapPad executable is not arm64-only"

non_system=$(otool -L "$binary" | tail -n +2 | awk '{print $1}' | \
    awk '$0 !~ /^\/System\/Library\// && $0 !~ /^\/usr\/lib\// {print}')
[[ -z "$non_system" ]] || \
    die "native SnapPad executable has non-system dynamic dependencies: $non_system"
if strings "$binary" | rg -F -q "$SNAPPAD_ROOT"; then
    die "native SnapPad executable embeds the local checkout path"
fi

forbidden=$(find "$app" -type f \( \
    -iname '*.z64' -o -iname '*.n64' -o -iname '*.v64' -o \
    -iname '*.elf' -o -iname '*.map' -o -iname '*.c' -o \
    -iname '*.cc' -o -iname '*.cpp' -o -iname '*.h' -o \
    -iname '*.hpp' \) -print)
[[ -z "$forbidden" ]] || \
    die "native SnapPad bundle contains forbidden ROM/build inputs: $forbidden"

note "Native macOS app audit passed (identity, arm64, system-only dylibs, path-clean, no ROM/source inputs)."
