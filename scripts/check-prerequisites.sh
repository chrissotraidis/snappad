#!/usr/bin/env bash
set -euo pipefail
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
source "$script_dir/lib/common.sh"

for command in git jq cmake ninja uv python3 cargo xcrun xcodebuild shasum rg; do
    require_command "$command"
done

[[ "$(uname -m)" == "arm64" ]] || die "Apple Silicon is required"
[[ -x /opt/homebrew/bin/cpp-16 ]] || die "GNU cpp-16 is missing (brew install gcc)"
xcrun -f metal >/dev/null 2>&1 || die "Xcode Metal toolchain is missing"

available_kib=$(df -Pk "$SNAPPAD_ROOT" | awk 'NR == 2 {print $4}')
[[ "$available_kib" =~ ^[0-9]+$ ]] || die "could not determine free disk space"
if (( available_kib < 20 * 1024 * 1024 )); then
    die "less than 20 GiB free; refusing a large generated build"
fi

note "Host prerequisites OK ($(uname -m), $(xcodebuild -version | head -n 1), uv $(uv --version | awk '{print $2}'))."
note "Free disk: $((available_kib / 1024 / 1024)) GiB. Keep one build tree per target."
