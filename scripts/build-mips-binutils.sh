#!/usr/bin/env bash
# Build the pinned local MIPS binutils used to inspect and rebuild Pokemon Snap.
set -euo pipefail
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
source "$script_dir/lib/common.sh"

for command in curl make shasum tar; do
    require_command "$command"
done

version=$(jq -er '.decomp.toolchain.mipsBinutils.version' "$SNAPPAD_LOCK")
tools_root="$SNAPPAD_ROOT/build-tools"
prefix="$tools_root/mips-binutils-$version"
archive="$tools_root/downloads/binutils-$version.tar.xz"
source_dir="$tools_root/binutils-$version"
build_dir="$tools_root/mips-binutils-$version-build"

if [[ -x "$prefix/bin/mips-linux-gnu-readelf" && \
      -x "$prefix/bin/mips-linux-gnu-as" ]]; then
    note "Local MIPS binutils already ready: $prefix"
    exit 0
fi

mkdir -p "$tools_root/downloads" "$build_dir"
curl -L --fail --retry 3 -o "$archive" \
    "$(jq -er '.decomp.toolchain.mipsBinutils.url' "$SNAPPAD_LOCK")"

expected=$(jq -er '.decomp.toolchain.mipsBinutils.sha512' "$SNAPPAD_LOCK")
actual=$(shasum -a 512 "$archive" | awk '{ print $1 }')
[[ "$actual" == "$expected" ]] || \
    die "GNU binutils checksum mismatch"

if [[ ! -x "$source_dir/configure" ]]; then
    tar -xf "$archive" -C "$tools_root"
fi
if [[ ! -f "$build_dir/Makefile" ]]; then
    (
        cd "$build_dir"
        "$source_dir/configure" \
            --prefix="$prefix" --target=mips-linux-gnu \
            --disable-gdb --disable-gprof --disable-nls --disable-werror \
            --without-zstd --without-debuginfod
    )
fi

build_jobs=$(configured_build_jobs)
make -C "$build_dir" ${build_jobs:+-j"$build_jobs"}
make -C "$build_dir" install
[[ -x "$prefix/bin/mips-linux-gnu-readelf" ]] || \
    die "local MIPS readelf was not produced"
[[ -x "$prefix/bin/mips-linux-gnu-as" ]] || \
    die "local MIPS assembler was not produced"
note "Local MIPS binutils ready: $prefix"
