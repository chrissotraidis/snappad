#!/usr/bin/env python3
"""Regression tests for fail-closed recompilation diagnostic review."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/audit-generation-logs.py"
SPEC = importlib.util.spec_from_file_location("snappad_audit_generation", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class GenerationAuditTests(unittest.TestCase):
    def test_clean_logs_are_accepted(self) -> None:
        interpreted, unresolved = MODULE.classify_lines(
            {"cpu.log": "Generated 1200 functions\n", "rsp.log": "Done\n"}, []
        )
        self.assertEqual(interpreted, [])
        self.assertEqual(unresolved, [])

    def test_unknown_diagnostic_fails_closed(self) -> None:
        interpreted, unresolved = MODULE.classify_lines(
            {"cpu.log": "warning: unpaired relocation\n"}, []
        )
        self.assertEqual(interpreted, [])
        self.assertEqual(len(unresolved), 1)

    def test_ambiguous_info_diagnostic_fails_closed(self) -> None:
        line = (
            "[Info] Ambiguous jal target 0x80032A20 in function Example, "
            "falling back to function lookup\n"
        )
        interpreted, unresolved = MODULE.classify_lines({"cpu.log": line}, [])
        self.assertEqual(interpreted, [])
        self.assertEqual(len(unresolved), 1)

    def test_indirect_tail_call_diagnostic_fails_closed(self) -> None:
        interpreted, unresolved = MODULE.classify_lines(
            {"cpu.log": "[Info] Indirect tail call in recomp_entrypoint\n"}, []
        )
        self.assertEqual(interpreted, [])
        self.assertEqual(len(unresolved), 1)

    def test_exact_interpretation_is_recorded(self) -> None:
        allowlist = MODULE.validate_allowlist(
            {
                "schemaVersion": 1,
                "entries": [
                    {
                        "pattern": "^warning: known fixture$",
                        "rationale": "Synthetic test diagnostic only.",
                    }
                ],
            }
        )
        interpreted, unresolved = MODULE.classify_lines(
            {"cpu.log": "warning: known fixture\n"}, allowlist
        )
        self.assertEqual(len(interpreted), 1)
        self.assertEqual(unresolved, [])

    def test_ambiguous_allowlist_is_rejected_at_classification(self) -> None:
        entries = [
            {"pattern": "warning", "rationale": "first"},
            {"pattern": "fixture", "rationale": "second"},
        ]
        interpreted, unresolved = MODULE.classify_lines(
            {"cpu.log": "warning: fixture\n"}, entries
        )
        self.assertEqual(interpreted, [])
        self.assertEqual(unresolved[0]["reason"], "matches multiple allowlist entries")

    def test_source_manifest_is_order_independent_and_content_sensitive(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "a.c"
            second = root / "lookup.cpp"
            first.write_text("one", encoding="utf-8")
            second.write_text("two", encoding="utf-8")
            baseline = MODULE.source_manifest([second, first], root)
            self.assertEqual(baseline, MODULE.source_manifest([first, second], root))
            second.write_text("changed", encoding="utf-8")
            self.assertNotEqual(baseline, MODULE.source_manifest([first, second], root))


if __name__ == "__main__":
    unittest.main()
