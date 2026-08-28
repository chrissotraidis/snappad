#!/usr/bin/env bash
# Build the exact Pokemon Snap ROM, ELF, and linker map from the pinned decomp.
set -euo pipefail
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
source "$script_dir/lib/common.sh"

usage() {
    printf 'usage: %s [--rom /absolute/path/to/user-rom]\n' "$(basename "$0")" >&2
    exit 64
}

rom_path=
while (($#)); do
    case "$1" in
        --rom) (($# >= 2)) || usage; rom_path=$2; shift 2 ;;
        *) usage ;;
    esac
done

"$script_dir/check-prerequisites.sh"
"$script_dir/verify-sources.sh"
"$script_dir/build-mips-binutils.sh"
binutils_version=$(jq -er '.decomp.toolchain.mipsBinutils.version' "$SNAPPAD_LOCK")
binutils_bin="$SNAPPAD_ROOT/build-tools/mips-binutils-$binutils_version/bin"
export PATH="$binutils_bin:$PATH"

# The decomp asks for mips-linux-gnu-cpp first. Binutils does not provide a C
# preprocessor, and Apple's /usr/bin/cpp is a clang compatibility driver that
# misparses this project's traditional assembly-preprocessing invocation.
# Supply the already-required Homebrew GNU cpp under the cross-prefixed name so
# configure.py records an unambiguous, reproducible tool in build.ninja.
gnu_cpp=$(command -v cpp-16)
[[ -x "$gnu_cpp" ]] || die "GNU cpp-16 is missing (brew install gcc)"
cross_cpp="$binutils_bin/mips-linux-gnu-cpp"
ln -sfn "$gnu_cpp" "$cross_cpp"
[[ "$(readlink "$cross_cpp")" == "$gnu_cpp" ]] || \
    die "could not install the scoped GNU cross-preprocessor shim"

if [[ -n "$rom_path" ]]; then
    "$script_dir/prepare-rom.sh" --rom "$rom_path"
fi

normalized="$SNAPPAD_GENERATED/rom/pokemonsnap.z64"
decomp="$SNAPPAD_REF/pokemonsnap"
[[ -f "$normalized" ]] || \
    die "normalized ROM missing; pass --rom /absolute/path or run scripts/prepare-rom.sh"

expected_sha=$(jq -er '.rom.sha1' "$SNAPPAD_LOCK")
actual_sha=$(shasum -a 1 "$normalized" | awk '{print $1}')
[[ "$actual_sha" == "$expected_sha" ]] || die "normalized ROM hash changed"
assert_clean "$decomp" "Pokemon Snap decomp"

decomp_rom="$decomp/pokemonsnap.z64"
if [[ -e "$decomp_rom" && ! -L "$decomp_rom" ]]; then
    die "refusing to replace unexpected non-symlink input at ref/pokemonsnap/pokemonsnap.z64"
fi
ln -sfn "$normalized" "$decomp_rom"

(
    cd "$decomp"
    uv sync --frozen
    uv run configure.py --setup
    "$script_dir/verify-decomp-toolchain.sh"
    uv run configure.py
    link_log="$SNAPPAD_LOGS/g1/decomp-link.log"
    mkdir -p "$(dirname "$link_log")"
    set +e
    ninja 2>&1 | tee "$link_log"
    ninja_status=${PIPESTATUS[0]}
    set -e
    if ((ninja_status != 0)); then
        # The pinned upstream currently omits some linker declarations for
        # labels inside raw data/BSS spans. Recover only names that carry an
        # auditable address, then let the exact-ROM checksum judge the result.
        "$script_dir/recover-decomp-address-symbols.py" \
            --log "$link_log" \
            --output build/snappad_undefined_syms.ld \
            --build-ninja build.ninja

        # Upstream's generated absolute symbol table currently overrides many
        # symbols that the compiled objects now define themselves. Prefer the
        # object definitions, while retaining the address contract carried by
        # decomp-style names. The filter's two audited subobject exceptions
        # preserve the compiler-computed hitbox and palette offsets.
        "$script_dir/filter-decomp-defined-symbols.py" \
            --nm "$binutils_bin/mips-linux-gnu-nm" \
            --objects build \
            --input undefined_syms_auto.txt \
            --output build/snappad_undefined_syms_filtered.txt \
            --corrections build/snappad_defined_symbol_corrections.ld \
            --build-ninja build.ninja
        ninja
    fi
    shasum -a 1 -c checksum.sha1
)

for output in build/pokemonsnap.z64 build/pokemonsnap.elf build/pokemonsnap.map; do
    [[ -s "$decomp/$output" ]] || die "expected decomp output missing: $output"
done

note "Exact decomp rebuild passed."
for output in build/pokemonsnap.z64 build/pokemonsnap.elf build/pokemonsnap.map; do
    size=$(stat -f '%z' "$decomp/$output")
    sha256=$(shasum -a 256 "$decomp/$output" | awk '{print $1}')
    printf '%s size=%s sha256=%s\n' "$output" "$size" "$sha256"
done

"$script_dir/record-g1-evidence.py"
