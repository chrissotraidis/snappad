#!/usr/bin/env python3
"""Regression tests for the fail-closed runtime MIPS payload audit."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/audit-dynamic-code.py"
SPEC = importlib.util.spec_from_file_location("snappad_audit_dynamic_code", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class DynamicCodeAuditTests(unittest.TestCase):
    def test_payload_range_is_derived_from_explicit_segment_end(self) -> None:
        document = """
  - { start: 0xAAA610, type: vpk0, align: 16, name: unk_segment_AA18E0_vpk0 }
  - [0xAAA65B]
"""
        self.assertEqual(MODULE.parse_payload_range(document), (0xAAA610, 0xAAA65B))

    def test_missing_explicit_end_is_rejected(self) -> None:
        document = """
- { start: 0xAAA610, type: vpk0, align: 16, name: unk_segment_AA18E0_vpk0 }
- { start: 0xAAA660, type: bin, name: next }
"""
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                MODULE.parse_payload_range(document)

    def test_objdump_decodes_every_big_endian_word_at_runtime_address(self) -> None:
        # addiu v0,zero,1; jr ra; three nops. GNU objdump normally collapses a
        # trailing zero run, which would make a whole-payload audit incomplete.
        payload = bytes.fromhex("2402000103e00008000000000000000000000000")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "payload.bin"
            path.write_bytes(payload)
            listing, mnemonics = MODULE.disassemble(path)
        self.assertIn("80200000", listing)
        self.assertEqual(sum(mnemonics.values()), 5)
        self.assertEqual(mnemonics["jr"], 1)
        self.assertEqual(mnemonics["nop"], 3)

    def test_exact_sp_payload_contract_rejects_a_changed_word(self) -> None:
        payload = b"".join(
            word.to_bytes(4, "big") for word in MODULE.EXPECTED_SP_CHECK_WORDS
        )
        review = MODULE.verify_sp_integrity_contract(payload)
        self.assertEqual(review["status"], "accepted")
        changed = bytearray(payload)
        changed[0] ^= 1
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                MODULE.verify_sp_integrity_contract(bytes(changed))


if __name__ == "__main__":
    unittest.main()
