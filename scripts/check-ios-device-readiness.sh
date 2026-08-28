#!/usr/bin/env bash
# Report whether this Mac can build and deploy a private SnapPad device app.
set -euo pipefail
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
source "$script_dir/lib/common.sh"

require_command jq
require_command security
require_command xcrun

team_id=${SNAPPAD_APPLE_TEAM_ID:-}
identity_output=$(security find-identity -v -p codesigning 2>&1)
identity_count=$(printf '%s\n' "$identity_output" | \
    awk '/^[[:space:]]*[0-9]+\)/ { count++ } END { print count + 0 }')

device_json=$(mktemp "${TMPDIR:-/tmp}/snappad-devices.XXXXXX")
trap 'rm -f "$device_json"' EXIT
xcrun devicectl list devices --quiet --json-output "$device_json"
device_count=$(jq -er '.result.devices | length' "$device_json")

ready=1
if [[ -z "$team_id" ]]; then
    note "MISSING  SNAPPAD_APPLE_TEAM_ID"
    ready=0
else
    note "READY    development team: $team_id"
fi
if ((identity_count == 0)); then
    note "MISSING  Apple code-signing identity"
    ready=0
else
    note "READY    code-signing identities: $identity_count"
fi
if ((device_count == 0)); then
    note "MISSING  paired physical iPhone or iPad"
    ready=0
else
    note "READY    CoreDevice targets: $device_count"
    jq -r '.result.devices[] | "         \(.deviceProperties.name // .hardwareProperties.marketingName // .identifier // "unnamed device") [\(.identifier // "unknown id")]"' \
        "$device_json"
fi

if ((ready == 0)); then
    die "physical-device prerequisites are incomplete; no build, install, or app data was changed"
fi
note "SnapPad physical-device prerequisites are ready."
