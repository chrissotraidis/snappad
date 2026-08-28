#!/usr/bin/env bash
# Run the source inventory in the pinned decomp's locked Python environment.
set -euo pipefail
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
source "$script_dir/lib/common.sh"

"$script_dir/verify-sources.sh"
(
    cd "$SNAPPAD_REF/pokemonsnap"
    uv sync --frozen
    uv run python "$script_dir/inventory-source-layout.py"
)
