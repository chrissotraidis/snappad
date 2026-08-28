#!/usr/bin/env bash

set -euo pipefail

SNAPPAD_ROOT=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
SNAPPAD_LOCK="$SNAPPAD_ROOT/dependencies.lock.json"
SNAPPAD_REF="$SNAPPAD_ROOT/ref"
SNAPPAD_GENERATED="$SNAPPAD_ROOT/generated"
SNAPPAD_LOGS="$SNAPPAD_ROOT/logs"

die() {
    printf 'error: %s\n' "$*" >&2
    exit 1
}

note() {
    printf '%s\n' "$*"
}

require_command() {
    command -v "$1" >/dev/null 2>&1 || die "required command not found: $1"
}

configured_build_jobs() {
    local build_jobs=${SNAPPAD_BUILD_JOBS:-}
    if [[ -n "$build_jobs" ]]; then
        [[ "$build_jobs" =~ ^[1-9][0-9]*$ ]] || \
            die "SNAPPAD_BUILD_JOBS must be a positive integer"
    fi
    printf '%s\n' "$build_jobs"
}

lock_value() {
    local source_name=$1
    local field=$2
    jq -er --arg name "$source_name" --arg field "$field" \
        '.sources[$name][$field]' "$SNAPPAD_LOCK"
}

assert_revision() {
    local checkout=$1
    local expected=$2
    local label=$3
    [[ -d "$checkout/.git" || -f "$checkout/.git" ]] || \
        die "missing checkout for $label: $checkout"
    local actual
    actual=$(git -C "$checkout" rev-parse HEAD)
    [[ "$actual" == "$expected" ]] || \
        die "$label revision mismatch: expected $expected, found $actual"
}

assert_clean() {
    local checkout=$1
    local label=$2
    [[ -z "$(git -C "$checkout" status --porcelain)" ]] || \
        die "$label checkout is modified: $checkout"
}

disable_push() {
    local checkout=$1
    if git -C "$checkout" remote get-url origin >/dev/null 2>&1; then
        git -C "$checkout" remote set-url --push origin DISABLED
    fi
}

clone_locked_source() {
    local key=$1
    local destination=$2
    local label=$3
    local url commit actual
    url=$(lock_value "$key" url)
    commit=$(lock_value "$key" commit)

    if [[ ! -d "$destination/.git" ]]; then
        git clone --filter=blob:none "$url" "$destination"
    fi

    actual=$(git -C "$destination" rev-parse HEAD)
    if [[ "$actual" != "$commit" ]]; then
        assert_clean "$destination" "$label"
        git -C "$destination" fetch --depth=1 origin "$commit"
        git -C "$destination" checkout --detach "$commit"
    fi

    assert_revision "$destination" "$commit" "$label"
    disable_push "$destination"
}
