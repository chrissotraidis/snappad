#!/usr/bin/env python3
"""Regression coverage for the dependency-free cadence trace summarizer."""

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "summarize_perf_trace.py"
SPEC = importlib.util.spec_from_file_location("summarize_perf_trace", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


HEADER = (
    "session_ms,interval_ms,input_polls,input_hz,screen_updates,screen_hz,"
    "presented_frames,presented_hz,present_intervals,mean_present_interval_ms,"
    "max_present_interval_ms,present_intervals_over_50_ms,"
    "present_intervals_over_100_ms,display_hz,focused,minimized\n"
)


class PerfTraceSummaryTests(unittest.TestCase):
    def write_trace(self, body: str) -> Path:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "trace.csv"
        path.write_text(HEADER + body, encoding="utf-8")
        return path

    def test_weighted_summary_and_range(self) -> None:
        path = self.write_trace(
            "1000,1000,60,60,60,60,30,30,30,33.000,40.000,0,0,60,1,0\n"
            "2000,500,30,60,30,60,10,20,10,50.000,120.000,2,1,60,1,0\n"
            "3000,1000,1,1,1,1,1,1,1,1000.000,1000.000,1,1,60,0,0\n"
        )
        rows = MODULE.load_rows(path, 1000, 2000)
        result = MODULE.summarize(rows)
        self.assertEqual(result["rows"], 2)
        self.assertAlmostEqual(result["input_hz"], 60.0)
        self.assertAlmostEqual(result["presented_hz"], 40.0 / 1.5)
        self.assertAlmostEqual(result["mean_present_interval_ms"], 37.25)
        self.assertEqual(result["max_present_interval_ms"], 120.0)
        self.assertEqual(result["present_intervals_over_50_ms"], 2)
        self.assertEqual(result["present_intervals_over_100_ms"], 1)

    def test_rejects_legacy_trace_without_interval_columns(self) -> None:
        path = self.write_trace("")
        path.write_text("session_ms,interval_ms\n1000,1000\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "missing columns"):
            MODULE.load_rows(path, None, None)


if __name__ == "__main__":
    unittest.main()
