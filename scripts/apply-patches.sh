#!/usr/bin/env bash
# Apply only reviewed game-neutral PaperPad patches to the exact ReCut pin.
set -euo pipefail
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
source "$script_dir/lib/common.sh"

recut="$SNAPPAD_REF/paper-mario-recut"
[[ -d "$recut/.git" ]] || die "Paper-Mario-ReCut is missing; run scripts/clone-sources.sh"
assert_revision "$recut" "$(lock_value paperMarioReCut commit)" "Paper-Mario-ReCut"

apply_one() {
    local patch=$1
    if git -C "$recut" apply --check "$patch" >/dev/null 2>&1; then
        git -C "$recut" apply "$patch"
        note "Applied: ${patch#"$SNAPPAD_ROOT/"}"
    elif git -C "$recut" apply --reverse --check "$patch" >/dev/null 2>&1; then
        note "Already applied: ${patch#"$SNAPPAD_ROOT/"}"
    else
        die "patch is neither cleanly applicable nor already applied: $patch"
    fi
}

for patch in "$SNAPPAD_ROOT"/port/patches/n64recomp/*.patch \
             "$SNAPPAD_ROOT"/port/patches/n64modernruntime/*.patch \
             "$SNAPPAD_ROOT"/port/patches/rt64/*.patch; do
    apply_one "$patch"
done

note "SnapPad game-neutral Apple/runtime patch stack is ready."
