#!/usr/bin/env python3
"""Regression coverage for SnapPad soak audio and memory summaries."""

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "summarize_soak_trace.py"
SPEC = importlib.util.spec_from_file_location("summarize_soak_trace", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class SoakTraceSummaryTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)

    def test_audio_summary_and_range(self) -> None:
        path = self.directory / "runtime.log"
        path.write_text(
            "noise\n"
            "[audio t=2.000s] callbacks=120 max_gap_us=21000 prequeue_zero=1 "
            "queue_us=20000 peak_queue_us=30000 over_100ms=0 "
            "conversion_errors=0 queue_errors=0\n"
            "[audio t=4.000s] callbacks=115 max_gap_us=120000 prequeue_zero=3 "
            "queue_us=25000 peak_queue_us=40000 over_100ms=1 "
            "conversion_errors=1 queue_errors=2\n",
            encoding="utf-8",
        )
        records = MODULE.load_audio_records(path, 3000, None)
        result = MODULE.summarize_audio(records)
        self.assertEqual(result["records"], 1)
        self.assertEqual(result["max_callback_gap_us"], 120000)
        self.assertEqual(result["records_over_100ms_gap"], 1)
        self.assertEqual(result["conversion_errors"], 1)
        self.assertEqual(result["queue_errors"], 2)

    def test_memory_regression_slope(self) -> None:
        path = self.directory / "memory.csv"
        path.write_text(
            "session_ms,rss_kib,vsz_kib,cpu_percent\n"
            "0,1000,2000,10.0\n"
            "60000,1060,2000,20.0\n"
            "120000,1120,2000,15.0\n",
            encoding="utf-8",
        )
        result = MODULE.summarize_memory(MODULE.load_memory_rows(path, None, None))
        self.assertEqual(result["rss_delta_kib"], 120)
        self.assertAlmostEqual(result["rss_slope_kib_per_minute"], 60.0)
        self.assertEqual(result["peak_cpu_percent"], 20.0)

    def test_rejects_missing_memory_columns(self) -> None:
        path = self.directory / "memory.csv"
        path.write_text("session_ms,rss_kib\n0,1000\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "missing columns"):
            MODULE.load_memory_rows(path, None, None)


if __name__ == "__main__":
    unittest.main()
