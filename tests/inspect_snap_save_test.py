#!/usr/bin/env python3
"""Regression coverage for the read-only Pokémon Snap save inspector."""

from __future__ import annotations

import importlib.util
import struct
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "inspect_snap_save.py"
SPEC = importlib.util.spec_from_file_location("inspect_snap_save", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class InspectSnapSaveTests(unittest.TestCase):
    def save_fixture(self, reported: dict[int, int]) -> Path:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        payload = bytearray(MODULE.FLASH_SIZE)
        payload[MODULE.VERSION_OFFSET:MODULE.VERSION_OFFSET + len(MODULE.VERSION)] = (
            MODULE.VERSION
        )
        for slot in range(len(MODULE.REPORT_SPECIES)):
            struct.pack_into(
                ">i",
                payload,
                MODULE.PHOTO_TABLE_OFFSET
                + slot * MODULE.PHOTO_SIZE
                + MODULE.PHOTO_VALID_OFFSET,
                -1,
            )
        slots = {pokemon_id: slot for slot, (pokemon_id, _) in enumerate(MODULE.REPORT_SPECIES)}
        for pokemon_id, score in reported.items():
            slot = slots[pokemon_id]
            struct.pack_into(">i", payload, MODULE.SCORE_TABLE_OFFSET + slot * 4, score)
            struct.pack_into(
                ">i",
                payload,
                MODULE.PHOTO_TABLE_OFFSET
                + slot * MODULE.PHOTO_SIZE
                + MODULE.PHOTO_VALID_OFFSET,
                0,
            )
        path = Path(directory.name) / "save.bin"
        path.write_bytes(payload)
        return path

    def test_reports_roster_and_score_without_modifying_save(self) -> None:
        path = self.save_fixture({16: 1400, 25: 3000, 151: 9000})
        before = path.read_bytes()
        result = MODULE.inspect_save(path)
        self.assertEqual(result["reported_count"], 3)
        self.assertEqual(result["total_score"], 13400)
        self.assertEqual([item["id"] for item in result["reported"]], [16, 25, 151])
        self.assertNotIn(16, [item["id"] for item in result["missing"]])
        self.assertEqual(path.read_bytes(), before)

    def test_rejects_wrong_size_and_version(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        short = Path(directory.name) / "short.bin"
        short.write_bytes(b"not a flash save")
        with self.assertRaisesRegex(ValueError, "expected 131072 bytes"):
            MODULE.inspect_save(short)

        invalid = Path(directory.name) / "invalid.bin"
        invalid.write_bytes(bytes(MODULE.FLASH_SIZE))
        with self.assertRaisesRegex(ValueError, "version marker"):
            MODULE.inspect_save(invalid)


if __name__ == "__main__":
    unittest.main()
