#!/usr/bin/env bash
# Apply reviewed patches to their exact pinned dependency checkouts.
set -euo pipefail
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
source "$script_dir/lib/common.sh"

recut="$SNAPPAD_REF/paper-mario-recut"
[[ -d "$recut/.git" ]] || die "Paper-Mario-ReCut is missing; run scripts/clone-sources.sh"
assert_revision "$recut" "$(lock_value paperMarioReCut commit)" "Paper-Mario-ReCut"
sdl2="$SNAPPAD_REF/SDL2"
[[ -d "$sdl2/.git" ]] || die "SDL2 is missing; run scripts/clone-sources.sh"
assert_revision "$sdl2" "$(lock_value sdl2 commit)" "SDL2"

apply_one() {
    local checkout=$1
    local patch=$2
    if git -C "$checkout" apply --check "$patch" >/dev/null 2>&1; then
        git -C "$checkout" apply "$patch"
        note "Applied: ${patch#"$SNAPPAD_ROOT/"}"
    elif git -C "$checkout" apply --reverse --check "$patch" >/dev/null 2>&1; then
        note "Already applied: ${patch#"$SNAPPAD_ROOT/"}"
    else
        die "patch is neither cleanly applicable nor already applied: $patch"
    fi
}

for patch in "$SNAPPAD_ROOT"/port/patches/n64recomp/*.patch \
             "$SNAPPAD_ROOT"/port/patches/n64modernruntime/*.patch \
             "$SNAPPAD_ROOT"/port/patches/rt64/*.patch; do
    apply_one "$recut" "$patch"
done

for patch in "$SNAPPAD_ROOT"/port/patches/sdl2/*.patch; do
    apply_one "$sdl2" "$patch"
done

note "SnapPad game-neutral Apple/runtime patch stack is ready."
