#!/usr/bin/env bash
# Run RSP configuration derivation in the pinned decomp Python environment.
set -euo pipefail
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
source "$script_dir/lib/common.sh"

"$script_dir/verify-sources.sh"
(
    cd "$SNAPPAD_REF/pokemonsnap"
    uv sync --frozen
    uv run python "$script_dir/generate-rsp-config.py"
)
