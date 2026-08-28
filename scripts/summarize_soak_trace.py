#!/usr/bin/env python3
"""Summarize SnapPad audio telemetry and resident-memory soak samples."""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any, Iterable


AUDIO_PREFIX = re.compile(r"^\[audio t=(?P<seconds>[0-9]+(?:\.[0-9]+)?)s\] (?P<fields>.*)$")
INTEGER_FIELD = re.compile(r"^(?P<key>[a-z0-9_]+)=(?P<value>-?[0-9]+)$")
MEMORY_COLUMNS = {"session_ms", "rss_kib", "vsz_kib", "cpu_percent"}


def load_audio_records(
    path: Path, from_ms: int | None, to_ms: int | None
) -> list[dict[str, int]]:
    records: list[dict[str, int]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = AUDIO_PREFIX.match(line)
        if match is None:
            continue
        session_ms = round(float(match.group("seconds")) * 1000.0)
        if from_ms is not None and session_ms < from_ms:
            continue
        if to_ms is not None and session_ms > to_ms:
            continue
        record = {"session_ms": session_ms}
        for token in match.group("fields").split():
            field = INTEGER_FIELD.match(token)
            if field is not None:
                record[field.group("key")] = int(field.group("value"))
        records.append(record)
    return records


def summarize_audio(records: Iterable[dict[str, int]]) -> dict[str, Any]:
    selected = list(records)
    if not selected:
        raise ValueError("no audio records matched the requested interval")

    required = {
        "callbacks",
        "max_gap_us",
        "prequeue_zero",
        "queue_us",
        "peak_queue_us",
        "over_100ms",
        "conversion_errors",
        "queue_errors",
    }
    for record in selected:
        missing = required.difference(record)
        if missing:
            raise ValueError(
                "audio record is missing fields: " + ", ".join(sorted(missing))
            )

    return {
        "records": len(selected),
        "start_session_ms": selected[0]["session_ms"],
        "end_session_ms": selected[-1]["session_ms"],
        "callbacks": sum(record["callbacks"] for record in selected),
        "max_callback_gap_us": max(record["max_gap_us"] for record in selected),
        "records_over_50ms_gap": sum(
            record["max_gap_us"] > 50_000 for record in selected
        ),
        "records_over_100ms_gap": sum(
            record["max_gap_us"] > 100_000 for record in selected
        ),
        "prequeue_zero": sum(record["prequeue_zero"] for record in selected),
        "final_queue_us": selected[-1]["queue_us"],
        "peak_queue_us": max(record["peak_queue_us"] for record in selected),
        "queue_over_100ms": sum(record["over_100ms"] for record in selected),
        "conversion_errors": sum(record["conversion_errors"] for record in selected),
        "queue_errors": sum(record["queue_errors"] for record in selected),
    }


def load_memory_rows(
    path: Path, from_ms: int | None, to_ms: int | None
) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = MEMORY_COLUMNS.difference(reader.fieldnames or ())
        if missing:
            raise ValueError(
                "memory trace is missing columns: " + ", ".join(sorted(missing))
            )
        rows = []
        for row in reader:
            session_ms = int(row["session_ms"])
            if from_ms is not None and session_ms < from_ms:
                continue
            if to_ms is not None and session_ms > to_ms:
                continue
            rows.append(row)
        return rows


def summarize_memory(rows: Iterable[dict[str, str]]) -> dict[str, Any]:
    selected = list(rows)
    if not selected:
        raise ValueError("no memory rows matched the requested interval")

    times = [int(row["session_ms"]) / 1000.0 for row in selected]
    rss = [int(row["rss_kib"]) for row in selected]
    mean_time = sum(times) / len(times)
    mean_rss = sum(rss) / len(rss)
    denominator = sum((value - mean_time) ** 2 for value in times)
    slope_kib_per_second = (
        sum(
            (time - mean_time) * (value - mean_rss)
            for time, value in zip(times, rss)
        )
        / denominator
        if denominator
        else 0.0
    )

    return {
        "rows": len(selected),
        "start_session_ms": int(selected[0]["session_ms"]),
        "end_session_ms": int(selected[-1]["session_ms"]),
        "first_rss_kib": rss[0],
        "last_rss_kib": rss[-1],
        "min_rss_kib": min(rss),
        "max_rss_kib": max(rss),
        "rss_delta_kib": rss[-1] - rss[0],
        "rss_slope_kib_per_minute": slope_kib_per_second * 60.0,
        "peak_cpu_percent": max(float(row["cpu_percent"]) for row in selected),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runtime_log", type=Path)
    parser.add_argument("memory_trace", type=Path)
    parser.add_argument("--from-ms", type=int)
    parser.add_argument("--to-ms", type=int)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        result = {
            "audio": summarize_audio(
                load_audio_records(args.runtime_log, args.from_ms, args.to_ms)
            ),
            "memory": summarize_memory(
                load_memory_rows(args.memory_trace, args.from_ms, args.to_ms)
            ),
        }
    except (OSError, ValueError) as error:
        raise SystemExit(f"summarize_soak_trace: {error}") from error

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
        return

    audio = result["audio"]
    memory = result["memory"]
    print(
        f"audio_records={audio['records']} "
        f"session={audio['start_session_ms']}..{audio['end_session_ms']}ms "
        f"max_gap={audio['max_callback_gap_us'] / 1000.0:.3f}ms"
    )
    print(
        f"audio_gap_records_over_50ms={audio['records_over_50ms_gap']} "
        f"over_100ms={audio['records_over_100ms_gap']} "
        f"conversion_errors={audio['conversion_errors']} "
        f"queue_errors={audio['queue_errors']}"
    )
    print(
        f"memory_rows={memory['rows']} "
        f"session={memory['start_session_ms']}..{memory['end_session_ms']}ms "
        f"rss={memory['first_rss_kib']}..{memory['last_rss_kib']}KiB "
        f"range={memory['min_rss_kib']}..{memory['max_rss_kib']}KiB"
    )
    print(
        f"rss_delta={memory['rss_delta_kib']}KiB "
        f"rss_slope={memory['rss_slope_kib_per_minute']:.3f}KiB/min "
        f"peak_cpu={memory['peak_cpu_percent']:.1f}%"
    )


if __name__ == "__main__":
    main()
