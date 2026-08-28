#!/usr/bin/env python3
"""Persist exact rebuild hashes and the evidence-derived boot entrypoint."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import platform
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROM_HASH_TOOL = ROOT / "build-host-tools/snappad_rom_xxh3"
GENERATOR_PATH = ROOT / "scripts/generate-n64recomp-config.py"
SPEC = importlib.util.spec_from_file_location("snappad_config_generator", GENERATOR_PATH)
if SPEC is None or SPEC.loader is None:
    raise SystemExit("error: could not load N64Recomp config generator")
GENERATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GENERATOR)


def digest(path: Path, algorithm: str) -> str:
    result = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def artifact(path: Path) -> dict[str, object]:
    if not path.is_file() or path.stat().st_size == 0:
        raise SystemExit(f"error: missing G1 artifact: {path}")
    return {
        "path": str(path),
        "size": path.stat().st_size,
        "sha256": digest(path, "sha256"),
    }


def main() -> None:
    subprocess.run([str(ROOT / "scripts/build-rom-hash-tool.sh")], check=True)
    lock = json.loads((ROOT / "dependencies.lock.json").read_text(encoding="utf-8"))
    normalized = ROOT / "generated/rom/pokemonsnap.z64"
    rebuilt = ROOT / "ref/pokemonsnap/build/pokemonsnap.z64"
    elf = GENERATOR.ELF
    linker_map = GENERATOR.MAP
    for path in (normalized, rebuilt, elf, linker_map, GENERATOR.READELF):
        if not path.is_file() or path.stat().st_size == 0:
            raise SystemExit(f"error: missing G1 artifact: {path}")

    expected_sha1 = lock["rom"]["sha1"]
    normalized_sha1 = digest(normalized, "sha1")
    rebuilt_sha1 = digest(rebuilt, "sha1")
    if normalized_sha1 != expected_sha1 or rebuilt_sha1 != expected_sha1:
        raise SystemExit("error: normalized/rebuilt ROM does not match the locked SHA-1")
    rom_xxh3 = subprocess.run(
        [str(ROM_HASH_TOOL), str(normalized)],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if re.fullmatch(r"0x[0-9A-F]{16}", rom_xxh3) is None:
        raise SystemExit(f"error: invalid ROM XXH3 output: {rom_xxh3!r}")

    sections = GENERATOR.read_sections()
    symbols = GENERATOR.read_symbols()
    entrypoint = GENERATOR.derive_entrypoint(symbols)
    header = GENERATOR.run_readelf("-h")
    header_match = re.search(r"Entry point address:\s*(0x[0-9a-fA-F]+)", header)
    if header_match is None:
        raise SystemExit("error: ELF header entrypoint disappeared")

    revision = subprocess.run(
        ["git", "-C", str(ROOT / "ref/pokemonsnap"), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    expected_revision = lock["sources"]["pokemonSnap"]["commit"]
    if revision != expected_revision:
        raise SystemExit(f"error: decomp revision mismatch: {revision}")

    evidence = {
        "schemaVersion": 1,
        "gate": "G1",
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "host": {"machine": platform.machine(), "platform": platform.platform()},
        "decompRevision": revision,
        "lockedRomSha1": expected_sha1,
        "romXxh3_64": rom_xxh3,
        "normalizedRom": {**artifact(normalized), "sha1": normalized_sha1},
        "rebuiltRom": {**artifact(rebuilt), "sha1": rebuilt_sha1},
        "elf": artifact(elf),
        "linkerMap": artifact(linker_map),
        "elfHeaderEntry": header_match.group(1),
        "derivedEntrypoint": f"0x{entrypoint:08X}",
        "elfSectionCount": len(sections),
        "elfSymbolCount": len(symbols),
        "exactRebuild": True,
    }
    output = ROOT / "generated/evidence/G1.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote verified G1 evidence: {output} (entrypoint 0x{entrypoint:08X})")


if __name__ == "__main__":
    main()
