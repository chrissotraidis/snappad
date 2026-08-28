#!/usr/bin/env python3
"""Check the ROM helper against xxHash's published XXH3 test vectors."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path


def hash_bytes(tool: Path, data: bytes) -> str:
    with tempfile.TemporaryDirectory() as directory:
        input_path = Path(directory) / "input.bin"
        input_path.write_bytes(data)
        return subprocess.run(
            [str(tool), str(input_path)],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: rom_xxh3_test.py /path/to/snappad_rom_xxh3")
    tool = Path(sys.argv[1])
    vectors = {
        b"": "0x2D06800538D394C2",
        b"abc": "0x78AF5F94892F3950",
    }
    for data, expected in vectors.items():
        actual = hash_bytes(tool, data)
        if actual != expected:
            raise SystemExit(f"XXH3 mismatch: expected {expected}, found {actual}")
    print("rom_xxh3_test: published vectors passed")


if __name__ == "__main__":
    main()
