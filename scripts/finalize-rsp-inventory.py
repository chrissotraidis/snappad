#!/usr/bin/env python3
"""Hash source-declared RSP ranges from the exact rebuilt Pokemon Snap ROM."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "dependencies.lock.json"
SOURCE_INVENTORY = ROOT / "generated/inventory/source-layout.json"
ROM = ROOT / "ref/pokemonsnap/build/pokemonsnap.z64"
OUT = ROOT / "generated/inventory/rsp-verified.json"


def digest(data: bytes, algorithm: str) -> str:
    result = hashlib.new(algorithm)
    result.update(data)
    return result.hexdigest()


def parse_hex(value: str) -> int:
    return int(value, 16)


def main() -> None:
    if not SOURCE_INVENTORY.is_file():
        raise SystemExit("error: source inventory missing; run scripts/inventory-source-layout.sh")
    if not ROM.is_file():
        raise SystemExit("error: exact rebuilt ROM missing; complete G1 first")

    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    inventory = json.loads(SOURCE_INVENTORY.read_text(encoding="utf-8"))
    rom = ROM.read_bytes()
    if len(rom) != lock["rom"]["size"]:
        raise SystemExit(f"error: rebuilt ROM size mismatch: {len(rom)}")
    if digest(rom, "sha1") != lock["rom"]["sha1"]:
        raise SystemExit("error: rebuilt ROM SHA-1 mismatch")

    expected_names = {
        "rsp/rspboot",
        "rsp/aspMain",
        "rsp/gspF3DEX2H.NoN.fifo",
        "rsp/gspL3DEX2H.fifo",
    }
    actual_names = {entry["name"] for entry in inventory["rspBlobs"]}
    if actual_names != expected_names:
        raise SystemExit(f"error: RSP source inventory changed: {sorted(actual_names)}")

    verified = []
    for entry in inventory["rspBlobs"]:
        start = parse_hex(entry["romStart"])
        end = parse_hex(entry["romEnd"])
        if not 0 <= start < end <= len(rom) or (start % 8) != 0 or (end % 8) != 0:
            raise SystemExit(f"error: invalid RSP range for {entry['name']}")
        payload = rom[start:end]
        verified.append(
            {
                **entry,
                "size": f"0x{len(payload):X}",
                "sha1": digest(payload, "sha1"),
                "sha256": digest(payload, "sha256"),
            }
        )

    output = {
        "schemaVersion": 1,
        "verifiedFromExactRebuild": True,
        "romSha1": lock["rom"]["sha1"],
        "rspBlobs": verified,
        "executionPolicy": {
            "rsp/rspboot": "runtime boot handling; verify task handoff",
            "rsp/aspMain": "RSPRecomp candidate; load address and indirect targets unresolved",
            "rsp/gspF3DEX2H.NoN.fifo": "RT64 graphics task handling",
            "rsp/gspL3DEX2H.fifo": "RT64 graphics task handling",
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote verified RSP inventory: {OUT}")


if __name__ == "__main__":
    main()
