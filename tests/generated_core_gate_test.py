#!/usr/bin/env python3
"""The generated-core build must fail before exact ROM-derived inputs exist."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    with tempfile.TemporaryDirectory() as directory:
        result = subprocess.run(
            [
                "cmake",
                "-S",
                str(ROOT),
                "-B",
                directory,
                "-G",
                "Ninja",
                "-DBUILD_TESTING=OFF",
                "-DSNAPPAD_BUILD_GENERATED_CORE=ON",
                f"-DSNAPPAD_GENERATED_ROOT={Path(directory) / 'absent-generated'}",
            ],
            capture_output=True,
            text=True,
        )
    output = result.stdout + result.stderr
    if result.returncode == 0:
        raise SystemExit("generated-core configure unexpectedly accepted absent AOT inputs")
    if "Missing verified generated core input" not in output:
        raise SystemExit(f"generated-core configure failed for the wrong reason:\n{output}")
    print("generated_core_gate_test: absent ROM-derived inputs rejected")


if __name__ == "__main__":
    main()
