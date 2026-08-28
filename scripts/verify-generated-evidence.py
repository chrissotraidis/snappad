#!/usr/bin/env python3
"""Reject stale or unaudited N64Recomp/RSPRecomp output before compilation."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = ROOT / "scripts/audit-generation-logs.py"
SPEC = importlib.util.spec_from_file_location("snappad_generation_audit", AUDIT_PATH)
if SPEC is None or SPEC.loader is None:
    raise SystemExit("error: could not load generation audit helpers")
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


def fail(message: str) -> "NoReturn":
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    evidence_path = AUDIT.OUT
    if not evidence_path.is_file():
        fail(f"missing G2 generation evidence: {evidence_path}")
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    if evidence.get("schemaVersion") != 2 or evidence.get("gate") != "G2-generation":
        fail("G2 generation evidence has an unsupported schema or gate")
    if evidence.get("accepted") is not True or evidence.get("unresolvedDiagnostics"):
        fail("G2 generation diagnostics were not accepted")

    required_inputs = {
        "g1EvidenceSha256": AUDIT.G1_EVIDENCE,
        "n64ConfigSha256": AUDIT.N64_CONFIG,
        "rspConfigSha256": AUDIT.RSP_CONFIG,
        "gameMetadataSha256": AUDIT.METADATA,
        "dynamicCodeEvidenceSha256": AUDIT.DYNAMIC_CODE_EVIDENCE,
    }
    recorded_inputs = evidence.get("inputs")
    if not isinstance(recorded_inputs, dict):
        fail("G2 generation evidence has no input identity map")
    for key, path in required_inputs.items():
        if not path.is_file() or recorded_inputs.get(key) != AUDIT.digest(path):
            fail(f"G2 generation evidence no longer matches {path}")

    cpu_sources = sorted((*AUDIT.CPU_OUTPUT.glob("*.c"), *AUDIT.CPU_OUTPUT.glob("*.cpp")))
    if evidence.get("generatedCpuSourceCount") != len(cpu_sources):
        fail("generated CPU source count no longer matches G2 evidence")
    if evidence.get("generatedCpuManifestSha256") != AUDIT.source_manifest(
        cpu_sources, AUDIT.CPU_OUTPUT
    ):
        fail("generated CPU source manifest no longer matches G2 evidence")
    if not AUDIT.RSP_OUTPUT.is_file() or evidence.get("generatedRspSha256") != AUDIT.digest(AUDIT.RSP_OUTPUT):
        fail("generated audio RSP no longer matches G2 evidence")
    print("Verified current G1/config/metadata/CPU/RSP identity against accepted G2 generation evidence.")


if __name__ == "__main__":
    main()
