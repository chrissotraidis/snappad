#!/usr/bin/env python3
"""Inventory source-declared Pokemon Snap segments and overlay load sites."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
DECOMP = ROOT / "ref/pokemonsnap"
SPLAT = DECOMP / "splat.yaml"
LOAD_SOURCE = DECOMP / "src/app_render/46270.c"
OUT = ROOT / "generated/inventory/source-layout.json"


def hex_value(value: int | None) -> str | None:
    return f"0x{value:X}" if isinstance(value, int) else None


def source_locations(pattern: str) -> list[dict[str, object]]:
    expression = re.compile(pattern)
    locations = []
    for path in sorted((DECOMP / "src").rglob("*.c")):
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if expression.search(line):
                locations.append(
                    {
                        "path": str(path.relative_to(DECOMP)),
                        "line": line_number,
                        "text": line.strip(),
                    }
                )
    return locations


def main() -> None:
    revision = subprocess.run(
        ["git", "-C", str(DECOMP), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    lock = json.loads((ROOT / "dependencies.lock.json").read_text())
    expected = lock["sources"]["pokemonSnap"]["commit"]
    if revision != expected:
        raise SystemExit(f"error: decomp revision mismatch: {revision}")

    document = yaml.safe_load(SPLAT.read_text(encoding="utf-8"))
    top_segments = document["segments"]
    starts = []
    for segment in top_segments:
        start = segment.get("start") if isinstance(segment, dict) else segment[0]
        if isinstance(start, int):
            starts.append(start)

    load_text = LOAD_SOURCE.read_text(encoding="utf-8")
    overlay_variables = {
        variable: segment
        for variable, segment in re.findall(
            r"Overlay\s+(\w+)\s*=\s*OVERLAY\((\w+)\);", load_text
        )
    }
    load_counts = {
        variable: len(re.findall(rf"dmaLoadOverlay\(&{re.escape(variable)}\)", load_text))
        for variable in overlay_variables
    }
    loaded_names = set(overlay_variables.values())

    code_segments = []
    rsp_blobs = []
    for segment in top_segments:
        if not isinstance(segment, dict) or segment.get("type") != "code":
            continue
        start = segment["start"]
        later = [candidate for candidate in starts if candidate > start]
        end = min(later) if later else lock["rom"]["size"]
        name = segment["name"]
        code_segments.append(
            {
                "name": name,
                "romStart": hex_value(start),
                "romEndUpperBound": hex_value(end),
                "vramStart": hex_value(segment.get("vram")),
                "bssSize": hex_value(segment.get("bss_size")),
                "exclusiveRamId": segment.get("exclusive_ram_id"),
                "declaredOverlay": name in loaded_names,
            }
        )

        subsegments = segment.get("subsegments", [])
        for index, subsegment in enumerate(subsegments):
            if not (isinstance(subsegment, list) and len(subsegment) >= 3
                    and subsegment[1] == "textbin"
                    and str(subsegment[2]).startswith("rsp/")):
                continue
            rsp_start = subsegment[0]
            following = [
                candidate[0]
                for candidate in subsegments[index + 1:]
                if isinstance(candidate, list) and isinstance(candidate[0], int)
            ]
            rsp_end = min(following) if following else end
            rsp_blobs.append(
                {
                    "name": subsegment[2],
                    "romStart": hex_value(rsp_start),
                    "romEnd": hex_value(rsp_end),
                    "size": hex_value(rsp_end - rsp_start),
                    "sha256": None,
                }
            )

    overlay_loads = [
        {
            "variable": variable,
            "segment": segment,
            "loadSiteCount": load_counts[variable],
        }
        for variable, segment in sorted(overlay_variables.items())
    ]
    instruction_cache_invalidations = source_locations(r"\bosInvalICache\s*\(")
    if len(instruction_cache_invalidations) != 1:
        raise SystemExit(
            "error: expected the single source-level I-cache invalidation in dmaLoadOverlay, "
            f"found {len(instruction_cache_invalidations)}"
        )
    vpk_loads = [
        location
        for location in source_locations(r"\bdmaReadVPK0\s*\(")
        if location["path"] != "src/sys/dma.c"
    ]
    if len(vpk_loads) != 3:
        raise SystemExit(f"error: expected three VPK0 load call sites, found {len(vpk_loads)}")
    runtime_mips_calls = source_locations(
        r"\(\(void\s*\(\*\)\(void\)\)\s*UNK_STUFF_VRAM\)\s*\(\)"
    )
    if len(runtime_mips_calls) != 1:
        raise SystemExit(
            f"error: expected one runtime-loaded MIPS call, found {len(runtime_mips_calls)}"
        )

    output = {
        "schemaVersion": 2,
        "sourceOnly": True,
        "warning": "ROM end bounds and hashes require the verified G1 ELF/map/ROM.",
        "decompRevision": revision,
        "codeSegments": code_segments,
        "overlayLoads": overlay_loads,
        "rspBlobs": rsp_blobs,
        "dynamicCodeAudit": {
            "instructionCacheInvalidations": instruction_cache_invalidations,
            "vpkLoads": vpk_loads,
            "runtimeLoadedMipsCalls": runtime_mips_calls,
            "classification": {
                "main_menu_vpk0": "data: sprites, textures, and animation structures",
                "intro_code_vpk0": "data: sprite content despite the historical segment name",
                "unk_segment_AA18E0_vpk0": "executable: decompressed to 0x80200000 and called",
            },
            "nativePolicy": (
                "Replace func_80364360_504770 with the bounded SP-integrity hook; "
                "never execute the decompressed MIPS payload on Apple targets."
            ),
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(
        f"Wrote {OUT}: {len(code_segments)} code segments, "
        f"{len(overlay_loads)} declared overlays, {len(rsp_blobs)} RSP blobs."
    )


if __name__ == "__main__":
    main()
