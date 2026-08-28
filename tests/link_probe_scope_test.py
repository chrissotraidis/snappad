#!/usr/bin/env python3
"""Ensure ROM-derived link fixtures can never enter the production app."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def target_body(cmake: str, declaration: str) -> str:
    start = cmake.find(declaration)
    if start < 0:
        raise SystemExit(f"missing CMake target declaration: {declaration}")
    end = cmake.find("\n    target_include_directories", start)
    if end < 0:
        raise SystemExit(f"could not isolate target declaration: {declaration}")
    return cmake[start:end]


def main() -> None:
    cmake = (ROOT / "CMakeLists.txt").read_text(encoding="utf-8")
    fixture = "tests/fixtures/native_link_probe_stubs.cpp"
    if cmake.count(fixture) != 1:
        raise SystemExit("native link fixture must appear in exactly one target")
    probe = target_body(cmake, "add_executable(snappad_native_link_probe")
    production = target_body(cmake, "add_executable(SnapPad\n")
    if fixture not in probe:
        raise SystemExit("native link fixture escaped its probe target")
    if "tests/fixtures" in production or "native_link_probe" in production:
        raise SystemExit("production SnapPad target contains link-probe fixtures")
    print("link_probe_scope_test: fixture symbols are isolated from production SnapPad")


if __name__ == "__main__":
    main()
