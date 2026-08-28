#!/usr/bin/env python3
"""Regression tests for evidence-derived Pokemon Snap RSP configuration."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import struct
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/generate-rsp-config.py"
SPEC = importlib.util.spec_from_file_location("snappad_generate_rsp", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class RspConfigTests(unittest.TestCase):
    def test_source_databin_range_is_derived(self) -> None:
        document = {
            "segments": [
                {
                    "subsegments": [
                        {"start": 0x100, "type": "databin", "name": "rsp/aspMain"},
                        {"start": 0x160, "type": "databin", "name": "rsp/next"},
                    ]
                }
            ]
        }
        self.assertEqual(
            MODULE.find_databin_range(document, "rsp/aspMain"), (0x100, 0x160)
        )

    def test_dispatch_targets_are_normalized_and_deduplicated(self) -> None:
        raw = [
            0x10EC,
            0x139C,
            0x119C,
            0x1A64,
            0x11C8,
            0x17EC,
            0x1208,
            0x127C,
            0x02B0,
            0x10EC,
            0,
            0,
            0,
            0,
            0,
            0,
        ]
        data = b"".join(struct.pack(">H", value) for value in raw)
        targets = MODULE.derive_dispatch_targets(data, 0, 0x04001080, 0xE20)
        self.assertIn(0x12B0, targets)
        self.assertEqual(targets.count(0x10EC), 1)
        self.assertEqual(len(targets), 9)

    def test_out_of_range_dispatch_target_is_rejected(self) -> None:
        raw = [0x1F00] + [0x1080 + index * 4 for index in range(7)] + [0] * 8
        data = b"".join(struct.pack(">H", value) for value in raw)
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                MODULE.derive_dispatch_targets(data, 0, 0x04001080, 0xE20)

    def test_dispatch_table_offset_comes_from_lh_jr_pair(self) -> None:
        lh_v0_0x10_v0 = (0x21 << 26) | (2 << 21) | (2 << 16) | 0x10
        jr_v0 = (2 << 21) | 0x08
        text = struct.pack(">III", 0, lh_v0_0x10_v0, jr_v0)
        self.assertEqual(MODULE.derive_dispatch_table_offset(text), 0x10)

    def test_boot_load_address_requires_rsp_i_type_instruction(self) -> None:
        boot = bytearray(MODULE.BOOT_SIZE)
        # The exact Pokémon Snap IPL3-derived boot uses ADDI here.
        struct.pack_into(">I", boot, 12, (0x08 << 26) | (8 << 16) | 0x1080)
        self.assertTrue(MODULE.boot_mentions_text_address(boot, 0x04001080))
        struct.pack_into(">I", boot, 12, 0x00001080)
        self.assertFalse(MODULE.boot_mentions_text_address(boot, 0x04001080))

    def test_rendered_config_has_no_unsupported_instruction_bypass(self) -> None:
        config = MODULE.render_config(0x3E580, 0xE20, 0x10, [0x1080, 0x1084])
        self.assertIn("text_address = 0x04001080", config)
        self.assertIn("aspMainData[0x10..0x2F]", config)
        self.assertIn('output_function_name = "aspMain"', config)
        self.assertNotIn("unsupported_instructions", config)


if __name__ == "__main__":
    unittest.main()
