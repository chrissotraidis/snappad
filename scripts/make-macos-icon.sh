#!/usr/bin/env bash
# Regenerate port/apple/AppIcon.icns for the native macOS app from the iOS
# artwork. iOS masks its full-bleed square icon itself; macOS does not, so the
# artwork is placed on the macOS icon grid (an 824x824 rounded square, corner
# radius ~185, centred on a transparent 1024x1024 canvas with a soft shadow)
# and rendered to every iconset size. Maintainer-only: the build uses the
# committed .icns and needs no image tools. Requires ImageMagick (magick).
set -euo pipefail
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
source "$script_dir/lib/common.sh"

src="$SNAPPAD_ROOT/port/apple/Assets.xcassets/AppIcon.appiconset/AppIcon-1024.png"
out="$SNAPPAD_ROOT/port/apple/AppIcon.icns"
command -v magick >/dev/null || die "ImageMagick is required to regenerate the icon (brew install imagemagick)"

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

magick "$src" -resize 824x824^ -gravity center -extent 824x824 "$work/art.png"
magick -size 824x824 xc:none -fill white -draw "roundrectangle 0,0 823,823 185,185" "$work/mask.png"
magick "$work/art.png" "$work/mask.png" -alpha off -compose CopyOpacity -composite "$work/shaped.png"
magick "$work/shaped.png" \( +clone -background black -shadow 35x14+0+10 \) +swap \
    -background none -layers merge +repage "$work/shadowed.png"
magick -size 1024x1024 xc:none "$work/shadowed.png" -gravity center -geometry +0+6 -composite \
    "$work/icon-1024.png"

iconset="$work/AppIcon.iconset"
mkdir -p "$iconset"
for size in 16 32 128 256 512; do
    sips -z "$size" "$size" "$work/icon-1024.png" --out "$iconset/icon_${size}x${size}.png" >/dev/null
    double=$((size * 2))
    sips -z "$double" "$double" "$work/icon-1024.png" \
        --out "$iconset/icon_${size}x${size}@2x.png" >/dev/null
done
iconutil -c icns -o "$out" "$iconset"
note "Wrote $out"
