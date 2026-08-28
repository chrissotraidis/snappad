#!/usr/bin/env python3
"""Fail closed until every N64Recomp/RSPRecomp diagnostic is interpreted."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
N64_LOG = ROOT / "logs/n64recomp-generate.log"
RSP_LOG = ROOT / "logs/rsprecomp-audio-generate.log"
ALLOWLIST = ROOT / "config/generation-warning-allowlist.json"
CPU_OUTPUT = ROOT / "generated/aot/snappad_recomp_out"
RSP_OUTPUT = ROOT / "generated/aot/rsp/aspMain.cpp"
N64_CONFIG = ROOT / "generated/aot/snappad-us.toml"
RSP_CONFIG = ROOT / "generated/aot/snappad-audio-rsp.toml"
METADATA = ROOT / "generated/aot/snappad_game_metadata.h"
G1_EVIDENCE = ROOT / "generated/evidence/G1.json"
DYNAMIC_CODE_EVIDENCE = ROOT / "generated/evidence/G2-dynamic-code.json"
OUT = ROOT / "generated/evidence/G2-generation.json"

DIAGNOSTIC = re.compile(
    r"\b(warning|error|failed|failure|unhandled|unsupported|unknown|ambiguous)\b"
    r"|\bindirect tail call\b",
    re.IGNORECASE,
)


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def source_manifest(paths: list[Path], root: Path) -> str:
    result = hashlib.sha256()
    for path in sorted(paths, key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        result.update(relative)
        result.update(b"\0")
        result.update(bytes.fromhex(digest(path)))
        result.update(b"\n")
    return result.hexdigest()


def validate_allowlist(document: dict) -> list[dict[str, str]]:
    if document.get("schemaVersion") != 1 or not isinstance(document.get("entries"), list):
        raise ValueError("allowlist must use schemaVersion 1 and an entries array")
    entries = []
    for index, entry in enumerate(document["entries"]):
        if not isinstance(entry, dict):
            raise ValueError(f"allowlist entry {index} is not an object")
        pattern = entry.get("pattern")
        rationale = entry.get("rationale")
        if not isinstance(pattern, str) or not pattern:
            raise ValueError(f"allowlist entry {index} has no pattern")
        if not isinstance(rationale, str) or not rationale.strip():
            raise ValueError(f"allowlist entry {index} has no rationale")
        re.compile(pattern)
        entries.append({"pattern": pattern, "rationale": rationale.strip()})
    return entries


def classify_lines(
    logs: dict[str, str], allowlist: list[dict[str, str]]
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    interpreted = []
    unresolved = []
    for log_name, text in logs.items():
        for line_number, line in enumerate(text.splitlines(), 1):
            if DIAGNOSTIC.search(line) is None:
                continue
            matches = [entry for entry in allowlist if re.search(entry["pattern"], line)]
            record = {
                "log": log_name,
                "line": line_number,
                "text": line,
            }
            if len(matches) == 1:
                interpreted.append({**record, "rationale": matches[0]["rationale"]})
            else:
                unresolved.append(
                    {
                        **record,
                        "reason": (
                            "no documented interpretation"
                            if not matches
                            else "matches multiple allowlist entries"
                        ),
                    }
                )
    return interpreted, unresolved


def main() -> None:
    for path, label in (
        (N64_LOG, "N64Recomp log"),
        (RSP_LOG, "RSPRecomp log"),
        (ALLOWLIST, "diagnostic allowlist"),
        (RSP_OUTPUT, "generated audio RSP source"),
        (N64_CONFIG, "N64Recomp config"),
        (RSP_CONFIG, "RSPRecomp config"),
        (METADATA, "generated game metadata"),
        (G1_EVIDENCE, "G1 evidence"),
        (DYNAMIC_CODE_EVIDENCE, "dynamic-code evidence"),
    ):
        if not path.is_file():
            raise SystemExit(f"error: missing {label}: {path}")
    cpu_sources = sorted((*CPU_OUTPUT.glob("*.c"), *CPU_OUTPUT.glob("*.cpp")))
    if not any(path.suffix == ".c" for path in cpu_sources) or not (CPU_OUTPUT / "lookup.cpp").is_file():
        raise SystemExit("error: incomplete N64Recomp output")

    try:
        allowlist = validate_allowlist(json.loads(ALLOWLIST.read_text(encoding="utf-8")))
    except (ValueError, json.JSONDecodeError, re.error) as exc:
        raise SystemExit(f"error: invalid generation diagnostic allowlist: {exc}")

    logs = {
        N64_LOG.name: N64_LOG.read_text(encoding="utf-8", errors="replace"),
        RSP_LOG.name: RSP_LOG.read_text(encoding="utf-8", errors="replace"),
    }
    dynamic_evidence = json.loads(
        DYNAMIC_CODE_EVIDENCE.read_text(encoding="utf-8")
    )
    if (
        dynamic_evidence.get("gate") != "G2-dynamic-code-review-input"
        or dynamic_evidence.get("gateComplete") is not True
        or dynamic_evidence.get("equivalenceReview", {}).get("status") != "accepted"
    ):
        raise SystemExit("error: dynamic-code equivalence review is not accepted")
    interpreted, unresolved = classify_lines(logs, allowlist)
    evidence = {
        "schemaVersion": 2,
        "gate": "G2-generation",
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "logs": {
            N64_LOG.name: {"sha256": digest(N64_LOG)},
            RSP_LOG.name: {"sha256": digest(RSP_LOG)},
        },
        "inputs": {
            "g1EvidenceSha256": digest(G1_EVIDENCE),
            "n64ConfigSha256": digest(N64_CONFIG),
            "rspConfigSha256": digest(RSP_CONFIG),
            "gameMetadataSha256": digest(METADATA),
            "dynamicCodeEvidenceSha256": digest(DYNAMIC_CODE_EVIDENCE),
        },
        "generatedCpuSourceCount": len(cpu_sources),
        "generatedCpuManifestSha256": source_manifest(cpu_sources, CPU_OUTPUT),
        "generatedRspSha256": digest(RSP_OUTPUT),
        "interpretedDiagnostics": interpreted,
        "unresolvedDiagnostics": unresolved,
        "accepted": not unresolved,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    if unresolved:
        for item in unresolved:
            print(
                f"unresolved: {item['log']}:{item['line']}: {item['text']}",
                file=sys.stderr,
            )
        raise SystemExit(
            "error: generation produced unresolved diagnostics; inspect the source, "
            "then document an exact pattern and rationale only if it is safe"
        )
    print(
        f"Generation diagnostics accepted: {len(interpreted)} interpreted, "
        f"{len(unresolved)} unresolved. Evidence: {OUT}"
    )


if __name__ == "__main__":
    main()
