#!/usr/bin/env python3
"""Summarize an opt-in SnapPad frame-cadence CSV without third-party tools."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Iterable


REQUIRED_COLUMNS = {
    "session_ms",
    "interval_ms",
    "input_polls",
    "screen_updates",
    "presented_frames",
    "present_intervals",
    "mean_present_interval_ms",
    "max_present_interval_ms",
    "present_intervals_over_50_ms",
    "present_intervals_over_100_ms",
}


def summarize(rows: Iterable[dict[str, str]]) -> dict[str, Any]:
    selected = list(rows)
    if not selected:
        raise ValueError("no cadence rows matched the requested interval")

    interval_ms = sum(int(row["interval_ms"]) for row in selected)
    if interval_ms <= 0:
        raise ValueError("cadence rows have no positive wall interval")
    seconds = interval_ms / 1000.0
    present_intervals = sum(int(row["present_intervals"]) for row in selected)
    weighted_present_ms = sum(
        int(row["present_intervals"]) * float(row["mean_present_interval_ms"])
        for row in selected
    )
    over_50 = sum(int(row["present_intervals_over_50_ms"]) for row in selected)
    over_100 = sum(int(row["present_intervals_over_100_ms"]) for row in selected)

    return {
        "rows": len(selected),
        "start_session_ms": int(selected[0]["session_ms"]),
        "end_session_ms": int(selected[-1]["session_ms"]),
        "wall_seconds": seconds,
        "input_hz": sum(int(row["input_polls"]) for row in selected) / seconds,
        "screen_hz": sum(int(row["screen_updates"]) for row in selected) / seconds,
        "presented_hz": sum(int(row["presented_frames"]) for row in selected) / seconds,
        "present_intervals": present_intervals,
        "mean_present_interval_ms": (
            weighted_present_ms / present_intervals if present_intervals else 0.0
        ),
        "max_present_interval_ms": max(
            float(row["max_present_interval_ms"]) for row in selected
        ),
        "present_intervals_over_50_ms": over_50,
        "present_intervals_over_100_ms": over_100,
        "late_over_50_percent": (
            over_50 * 100.0 / present_intervals if present_intervals else 0.0
        ),
        "late_over_100_percent": (
            over_100 * 100.0 / present_intervals if present_intervals else 0.0
        ),
    }


def load_rows(path: Path, from_ms: int | None, to_ms: int | None) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = REQUIRED_COLUMNS.difference(reader.fieldnames or ())
        if missing:
            raise ValueError(f"trace is missing columns: {', '.join(sorted(missing))}")
        rows = []
        for row in reader:
            session_ms = int(row["session_ms"])
            if from_ms is not None and session_ms < from_ms:
                continue
            if to_ms is not None and session_ms > to_ms:
                continue
            rows.append(row)
        return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace", type=Path)
    parser.add_argument("--from-ms", type=int)
    parser.add_argument("--to-ms", type=int)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        result = summarize(load_rows(args.trace, args.from_ms, args.to_ms))
    except (OSError, ValueError) as error:
        raise SystemExit(f"summarize_perf_trace: {error}") from error

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
        return

    print(
        f"rows={result['rows']} wall={result['wall_seconds']:.3f}s "
        f"session={result['start_session_ms']}..{result['end_session_ms']}ms"
    )
    print(
        f"input={result['input_hz']:.3f}Hz "
        f"screen={result['screen_hz']:.3f}Hz "
        f"presented={result['presented_hz']:.3f}Hz"
    )
    print(
        f"present_intervals={result['present_intervals']} "
        f"mean={result['mean_present_interval_ms']:.3f}ms "
        f"max={result['max_present_interval_ms']:.3f}ms"
    )
    print(
        f"over_50ms={result['present_intervals_over_50_ms']} "
        f"({result['late_over_50_percent']:.3f}%) "
        f"over_100ms={result['present_intervals_over_100_ms']} "
        f"({result['late_over_100_percent']:.3f}%)"
    )


if __name__ == "__main__":
    main()
