#!/usr/bin/env python3
"""Generate the Pokemon Snap audio RSPRecomp config from verified ROM bytes."""

from __future__ import annotations

import hashlib
import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "dependencies.lock.json"
ROM = ROOT / "ref/pokemonsnap/build/pokemonsnap.z64"
SPLAT = ROOT / "ref/pokemonsnap/splat.yaml"
RSP_INVENTORY = ROOT / "generated/inventory/rsp-verified.json"
G1_EVIDENCE = ROOT / "generated/evidence/G1.json"
OUT = ROOT / "generated/aot/snappad-audio-rsp.toml"
RSP_OUTPUT = ROOT / "generated/aot/rsp/aspMain.cpp"

TEXT_NAME = "rsp/aspMain"
TEXT_ADDRESS = 0x04001080
BOOT_ROM_OFFSET = 0xB70
BOOT_SIZE = 0x100


def fail(message: str) -> "NoReturn":
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(1)


def digest(path: Path, algorithm: str) -> str:
    result = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def find_databin_range(document: dict, name: str) -> tuple[int, int]:
    matches: list[tuple[list, int]] = []
    for segment in document.get("segments", []):
        if not isinstance(segment, dict):
            continue
        subsegments = segment.get("subsegments", [])
        for index, subsegment in enumerate(subsegments):
            if (
                isinstance(subsegment, dict)
                and subsegment.get("type") == "databin"
                and subsegment.get("name") == name
            ):
                matches.append((subsegments, index))
    if len(matches) != 1:
        fail(f"expected one databin named {name}, found {len(matches)}")

    subsegments, index = matches[0]
    start = subsegments[index].get("start")
    later_starts = []
    for candidate in subsegments[index + 1 :]:
        candidate_start = (
            candidate.get("start") if isinstance(candidate, dict)
            else candidate[0] if isinstance(candidate, list) and candidate else None
        )
        if isinstance(candidate_start, int):
            later_starts.append(candidate_start)
    if not isinstance(start, int) or not later_starts:
        fail(f"could not derive ROM range for databin {name}")
    return start, min(later_starts)


def derive_dispatch_table_offset(text: bytes) -> int:
    """Find the DMEM halfword table loaded immediately before `jr target`."""
    matches: list[int] = []
    words = [word[0] for word in struct.iter_unpack(">I", text)]
    for load, branch in zip(words, words[1:]):
        if load >> 26 != 0x21:  # LH
            continue
        target_register = (load >> 16) & 0x1F
        is_jr_target = (
            branch >> 26 == 0
            and branch & 0x3F == 0x08
            and (branch >> 21) & 0x1F == target_register
        )
        if is_jr_target:
            immediate = load & 0xFFFF
            if immediate & 0x8000:
                immediate -= 0x10000
            matches.append(immediate)
    if len(matches) != 1 or matches[0] < 0 or matches[0] % 2 != 0:
        fail(f"expected one aligned audio dispatch-table load, found {matches}")
    return matches[0]


def derive_dispatch_targets(
    data: bytes, table_offset: int, text_start: int, text_size: int
) -> list[int]:
    table = data[table_offset : table_offset + 0x20]
    if len(table) != 0x20:
        fail("aspMain data is too short for its command dispatch table")
    text_pc = text_start & 0x1FFF
    text_end = text_pc + text_size
    targets = set()
    for (raw_target,) in struct.iter_unpack(">H", table):
        if raw_target == 0:
            continue
        target = 0x1000 | (raw_target & 0x0FFF)
        if target % 4 != 0 or not text_pc <= target < text_end:
            fail(f"aspMain dispatch target is outside text: 0x{target:04X}")
        targets.add(target)
    if len(targets) < 8:
        fail(f"aspMain dispatch table exposed only {len(targets)} unique handlers")
    return sorted(targets)


def boot_mentions_text_address(boot: bytes, text_address: int) -> bool:
    if len(boot) != BOOT_SIZE or len(boot) % 4 != 0:
        return False
    immediate = text_address & 0xFFFF
    for (word,) in struct.iter_unpack(">I", boot):
        opcode = word >> 26
        # This IPL3 boot uses ADDI (0x08) to materialize 0x1080; accept the
        # three immediate-form instructions that can establish that constant.
        if opcode in (0x08, 0x09, 0x0D) and (word & 0xFFFF) == immediate:
            return True
    return False


def render_config(
    text_offset: int, text_size: int, table_offset: int, targets: list[int]
) -> str:
    target_lines = ", ".join(f"0x{target:04X}" for target in targets)
    return f'''# Pokemon Snap US aspMain audio microcode.
# Generated from the exact G1 ROM by scripts/generate-rsp-config.py.
# rspboot loads task microcode after its 0x80-byte bootstrap at IMEM 0x1080.
text_offset = 0x{text_offset:X}
text_size = 0x{text_size:X}
text_address = 0x{TEXT_ADDRESS:08X}
rom_file_path = "{ROM}"
output_file_path = "{RSP_OUTPUT}"
output_function_name = "aspMain"

# Unique nonzero big-endian halfwords from the microcode-derived
# aspMainData[0x{table_offset:02X}..0x{table_offset + 0x1F:02X}] dispatch table,
# normalized into the RSP's 0x1000-based IMEM address window.
extra_indirect_branch_targets = [
    {target_lines}
]
'''


def main() -> None:
    import yaml

    for path, label in (
        (ROM, "exact rebuilt ROM"),
        (SPLAT, "source segment map"),
        (RSP_INVENTORY, "verified RSP inventory"),
        (G1_EVIDENCE, "G1 evidence"),
    ):
        if not path.is_file() or path.stat().st_size == 0:
            fail(f"missing {label}: {path}")

    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    evidence = json.loads(G1_EVIDENCE.read_text(encoding="utf-8"))
    inventory = json.loads(RSP_INVENTORY.read_text(encoding="utf-8"))
    if digest(ROM, "sha1") != lock["rom"]["sha1"]:
        fail("rebuilt ROM SHA-1 mismatch")
    if evidence.get("rebuiltRom", {}).get("sha256") != digest(ROM, "sha256"):
        fail("G1 evidence no longer matches rebuilt ROM")
    if not inventory.get("verifiedFromExactRebuild"):
        fail("RSP inventory is not verified from the exact rebuild")

    entries = [entry for entry in inventory.get("rspBlobs", []) if entry["name"] == TEXT_NAME]
    if len(entries) != 1:
        fail(f"expected one verified {TEXT_NAME} entry, found {len(entries)}")
    text_offset = int(entries[0]["romStart"], 16)
    text_end = int(entries[0]["romEnd"], 16)
    text_size = text_end - text_offset
    if text_offset != 0x3E580 or text_size != 0xE20:
        fail(f"unexpected aspMain text range: 0x{text_offset:X}+0x{text_size:X}")

    rom = ROM.read_bytes()
    boot = rom[BOOT_ROM_OFFSET : BOOT_ROM_OFFSET + BOOT_SIZE]
    if not boot_mentions_text_address(boot, TEXT_ADDRESS):
        fail("IPL3-derived rspboot does not prove an IMEM 0x1080 task-text load")

    document = yaml.safe_load(SPLAT.read_text(encoding="utf-8"))
    data_start, data_end = find_databin_range(document, TEXT_NAME)
    text = rom[text_offset:text_end]
    table_offset = derive_dispatch_table_offset(text)
    targets = derive_dispatch_targets(
        rom[data_start:data_end], table_offset, TEXT_ADDRESS, text_size
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        render_config(text_offset, text_size, table_offset, targets),
        encoding="utf-8",
    )
    print(
        f"Wrote {OUT}: aspMain 0x{text_offset:X}+0x{text_size:X} at "
        f"0x{TEXT_ADDRESS:08X}, DMEM table 0x{table_offset:X}, "
        f"{len(targets)} indirect targets."
    )


if __name__ == "__main__":
    main()
