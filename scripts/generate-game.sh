#!/usr/bin/env bash
# Generate Pokemon Snap AOT C sources from verified rebuild artifacts.
set -euo pipefail
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
source "$script_dir/lib/common.sh"

"$script_dir/verify-sources.sh"
"$script_dir/build-mips-binutils.sh"
"$script_dir/inventory-source-layout.sh"

recompiler="$SNAPPAD_ROOT/build-host-tools/N64Recomp"
rsp_recompiler="$SNAPPAD_ROOT/build-host-tools/RSPRecomp"
[[ -x "$recompiler" ]] || \
    die "native N64Recomp missing; run scripts/build-host-tools.sh"
[[ -x "$rsp_recompiler" ]] || \
    die "native RSPRecomp missing; run scripts/build-host-tools.sh"

"$script_dir/generate-n64recomp-config.py"
"$script_dir/audit-dynamic-code.py"
"$script_dir/finalize-rsp-inventory.py"
"$script_dir/generate-rsp-config.sh"
config="$SNAPPAD_GENERATED/aot/snappad-us.toml"
rsp_config="$SNAPPAD_GENERATED/aot/snappad-audio-rsp.toml"
output="$SNAPPAD_GENERATED/aot/snappad_recomp_out"
log="$SNAPPAD_LOGS/n64recomp-generate.log"
audio_rsp_output="$SNAPPAD_GENERATED/aot/rsp/aspMain.cpp"
audio_rsp_log="$SNAPPAD_LOGS/rsprecomp-audio-generate.log"
mkdir -p "$output" "$SNAPPAD_LOGS"

"$recompiler" "$config" 2>&1 | tee "$log"
"$rsp_recompiler" "$rsp_config" 2>&1 | tee "$audio_rsp_log"
generated_count=$(find "$output" -type f -name '*.c' | wc -l | tr -d ' ')
(( generated_count > 0 )) || die "N64Recomp produced no C sources"
[[ -s "$output/lookup.cpp" ]] || die "N64Recomp did not produce lookup.cpp"
[[ -s "$audio_rsp_output" ]] || die "RSPRecomp did not produce aspMain.cpp"
"$script_dir/audit-generation-logs.py"
note "Generated $generated_count AOT C sources and audio RSP source; logs: $log, $audio_rsp_log"
