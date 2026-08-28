#!/usr/bin/env python3
"""Extract and disassemble Pokemon Snap's one runtime MIPS payload.

The source decomp shows that ``unk_segment_AA18E0_vpk0`` is decompressed to
0x80200000 and called. Apple builds replace that route with a native hook, so
the exact payload must remain visible for equivalence review instead of being
silently discarded by AOT generation.
"""

from __future__ import annotations

import hashlib
import json
import re
import struct
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DECOMP = ROOT / "ref/pokemonsnap"
ROM = ROOT / "generated/rom/pokemonsnap.z64"
SPLAT = DECOMP / "splat.yaml"
G1_EVIDENCE = ROOT / "generated/evidence/G1.json"
OBJDUMP = ROOT / "build-tools/mips-binutils-2.46.1/bin/mips-linux-gnu-objdump"
PAYLOAD_NAME = "unk_segment_AA18E0_vpk0"
LOAD_ADDRESS = 0x80200000
PAYLOAD_OUT = ROOT / "generated/aot/dynamic/unk_segment_AA18E0_vpk0.bin"
DISASSEMBLY_OUT = ROOT / "generated/aot/dynamic/unk_segment_AA18E0_vpk0.s"
EVIDENCE_OUT = ROOT / "generated/evidence/G2-dynamic-code.json"
CALLER = DECOMP / "src/app_level/504770.c"
NATIVE_HOOK = ROOT / "port/runtime/snappad_game_hooks.cpp"

# Exact US payload decoded below. It reads bytes at load_address-{0x10,0x0C},
# writes 0xFF to load_address-8 when either is zero (else writes zero), then
# returns. The original caller converts that byte into PFID_ILLEGAL_COPY.
EXPECTED_SP_CHECK_WORDS = (
    0x3C0E8020, 0x91CFFFF0, 0x241800FF, 0x3C198020,
    0x15E00003, 0x3C088020, 0x03E00008, 0xA338FFF8,
    0x9109FFF4, 0x240A00FF, 0x3C0B8020, 0x15200003,
    0x3C0C8020, 0x03E00008, 0xA16AFFF8, 0xA180FFF8,
    0x03E00008, 0x00000000, 0x00000000, 0x00000000,
)


def fail(message: str) -> "NoReturn":
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(1)


def digest(path: Path, algorithm: str = "sha256") -> str:
    result = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def parse_payload_range(splat_text: str, name: str = PAYLOAD_NAME) -> tuple[int, int]:
    declaration = re.compile(
        rf"^\s*-\s*\{{\s*start:\s*(0x[0-9A-Fa-f]+),\s*type:\s*vpk0,"
        rf"[^\n}}]*\bname:\s*{re.escape(name)}\s*\}}\s*$",
        re.MULTILINE,
    )
    matches = list(declaration.finditer(splat_text))
    if len(matches) != 1:
        fail(f"expected one {name} VPK0 declaration, found {len(matches)}")
    start = int(matches[0].group(1), 16)
    tail = splat_text[matches[0].end() :]
    end_match = re.match(r"\s*-\s*\[\s*(0x[0-9A-Fa-f]+)\s*\]", tail)
    if end_match is None:
        fail(f"{name} declaration is not followed by an explicit ROM end")
    end = int(end_match.group(1), 16)
    if not 0 <= start < end or end - start > 0x10000:
        fail(f"implausible {name} ROM range: 0x{start:X}..0x{end:X}")
    return start, end


def decompress_payload(compressed: bytes) -> tuple[bytes, int]:
    tools_dir = DECOMP / "tools"
    sys.path.insert(0, str(tools_dir))
    try:
        from vpk0_codec import Vpk0DecompressionError, decompress_vpk0
    except ImportError as exc:
        fail(f"could not import the pinned VPK0 codec: {exc}")
    finally:
        sys.path.pop(0)

    try:
        payload, consumed = decompress_vpk0(compressed)
    except Vpk0DecompressionError as exc:
        fail(f"could not decompress {PAYLOAD_NAME}: {exc}")
    if consumed != len(compressed):
        fail(
            f"{PAYLOAD_NAME} consumed 0x{consumed:X} of its explicit "
            f"0x{len(compressed):X}-byte ROM range"
        )
    if not payload or len(payload) > 0x10000 or len(payload) % 4 != 0:
        fail(f"implausible executable payload size: 0x{len(payload):X}")
    return payload, consumed


def disassemble(payload_path: Path, objdump: Path = OBJDUMP) -> tuple[str, Counter[str]]:
    if not objdump.is_file() or not objdump.stat().st_mode & 0o111:
        fail(f"missing executable MIPS objdump: {objdump}")
    result = subprocess.run(
        [
            str(objdump),
            "-D",
            "--disassemble-zeroes",
            "-b", "binary",
            "-m", "mips:4300",
            "-EB",
            f"--adjust-vma=0x{LOAD_ADDRESS:08X}",
            str(payload_path),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        fail(f"MIPS disassembly failed: {result.stderr.strip()}")
    instruction = re.compile(
        r"^\s*[0-9a-fA-F]+:\s+(?:[0-9a-fA-F]{8}\s+)+([.$A-Za-z_][.$A-Za-z0-9_]*)"
    )
    mnemonics: Counter[str] = Counter()
    for line in result.stdout.splitlines():
        match = instruction.match(line)
        if match:
            mnemonics[match.group(1)] += 1
    expected_count = payload_path.stat().st_size // 4
    if sum(mnemonics.values()) != expected_count:
        fail(
            f"objdump decoded {sum(mnemonics.values())} of "
            f"{expected_count} payload words"
        )
    return result.stdout, mnemonics


def verify_sp_integrity_contract(payload: bytes) -> dict[str, object]:
    words = tuple(word[0] for word in struct.iter_unpack(">I", payload))
    if words != EXPECTED_SP_CHECK_WORDS:
        fail("runtime MIPS payload no longer matches the reviewed SP-integrity routine")

    caller = CALLER.read_text(encoding="utf-8")
    for statement in (
        "UNK_STUFF_SP_IMEM_OK = gSPImemOkay;",
        "UNK_STUFF_SP_DMEM_OK = gSPDmemOkay;",
        "if (UNK_STUFF_MINUS_8 != 0)",
        "setPlayerFlag(PFID_ILLEGAL_COPY, true);",
    ):
        if statement not in caller:
            fail(f"SP-integrity caller contract changed: {statement}")

    hook = NATIVE_HOOK.read_text(encoding="utf-8")
    for statement in (
        "if (sp_imem_ok && sp_dmem_ok)",
        "context->r4 = pokemon_snap::generated::illegal_copy_player_flag;",
        "context->r5 = 1;",
        "setPlayerFlag(rdram, context);",
    ):
        if statement not in hook:
            fail(f"native SP-integrity replacement contract changed: {statement}")

    return {
        "status": "accepted",
        "payloadSemantics": (
            "writes 0xFF when either copied SP-integrity byte is zero; "
            "writes zero when both are nonzero"
        ),
        "callerSemantics": (
            "sets PFID_ILLEGAL_COPY when the payload result byte is nonzero"
        ),
        "nativeSemantics": (
            "sets PFID_ILLEGAL_COPY exactly when either source integrity byte is zero"
        ),
        "hostRegression": "snappad_sp_integrity_hook",
    }


def verify_g1() -> dict[str, object]:
    for path, label in (
        (ROM, "normalized ROM"),
        (SPLAT, "decomp segment map"),
        (G1_EVIDENCE, "G1 evidence"),
    ):
        if not path.is_file() or path.stat().st_size == 0:
            fail(f"missing {label}: {path}")
    evidence = json.loads(G1_EVIDENCE.read_text(encoding="utf-8"))
    if evidence.get("gate") != "G1" or evidence.get("exactRebuild") is not True:
        fail("G1 evidence does not certify an exact rebuild")
    recorded = evidence.get("normalizedRom", {})
    if not isinstance(recorded, dict) or recorded.get("sha256") != digest(ROM):
        fail("G1 evidence no longer matches the normalized ROM")
    return evidence


def main() -> None:
    g1 = verify_g1()
    start, end = parse_payload_range(SPLAT.read_text(encoding="utf-8"))
    rom = ROM.read_bytes()
    if end > len(rom):
        fail(f"{PAYLOAD_NAME} range extends past the normalized ROM")
    compressed = rom[start:end]
    payload, consumed = decompress_payload(compressed)
    equivalence = verify_sp_integrity_contract(payload)

    PAYLOAD_OUT.parent.mkdir(parents=True, exist_ok=True)
    PAYLOAD_OUT.write_bytes(payload)
    disassembly, mnemonics = disassemble(PAYLOAD_OUT)
    DISASSEMBLY_OUT.write_text(disassembly, encoding="utf-8")

    evidence = {
        "schemaVersion": 1,
        "gate": "G2-dynamic-code-review-input",
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "g1NormalizedRomSha256": g1["normalizedRom"]["sha256"],
        "sourceSegment": PAYLOAD_NAME,
        "romRange": {"start": f"0x{start:X}", "end": f"0x{end:X}"},
        "compressedSize": len(compressed),
        "compressedBytesConsumed": consumed,
        "loadAddress": f"0x{LOAD_ADDRESS:08X}",
        "payload": {
            "path": str(PAYLOAD_OUT),
            "size": len(payload),
            "sha256": digest(PAYLOAD_OUT),
        },
        "disassembly": {
            "path": str(DISASSEMBLY_OUT),
            "instructionCount": sum(mnemonics.values()),
            "mnemonics": dict(sorted(mnemonics.items())),
        },
        "nativeReplacement": "SnapPad_RunSPIntegrityCheck",
        "equivalenceReview": equivalence,
        "gateComplete": True,
    }
    EVIDENCE_OUT.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE_OUT.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(
        f"Extracted {len(payload)} bytes ({sum(mnemonics.values())} MIPS words) "
        f"from {PAYLOAD_NAME}; review {DISASSEMBLY_OUT} before accepting G2."
    )


if __name__ == "__main__":
    main()
