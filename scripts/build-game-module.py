#!/usr/bin/env python3
"""Compile an iOS module from existing verified G2 inputs without changing them.

This maintainer entrypoint does not replace the complete private ROM rebuild.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from module_contract import ROOT, input_record, verify_inputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generated-dir", type=Path, required=True)
    parser.add_argument("--source-dir", type=Path, default=ROOT / "ref/paper-mario-recut")
    parser.add_argument("--toolchain", type=Path, required=True)
    parser.add_argument("--build-dir", type=Path, default=ROOT / "build/module")
    parser.add_argument("--jobs", type=int, default=2)
    args = parser.parse_args()
    if args.jobs < 1:
        parser.error("--jobs must be positive")
    generated, source, build = args.generated_dir.resolve(), args.source_dir.resolve(), args.build_dir.resolve()
    record = input_record(generated, source)
    build.mkdir(parents=True, exist_ok=True)
    receipt = build / "module-inputs.json"
    receipt.write_text(json.dumps(record, sort_keys=True, indent=2) + "\n")
    subprocess.run(["cmake", "--fresh", "-S", str(ROOT / "cmake/game-module"), "-B", str(build), "-G", "Ninja",
                    "-DCMAKE_BUILD_TYPE=Release", f"-DCMAKE_TOOLCHAIN_FILE={args.toolchain.resolve()}",
                    f"-DPython3_EXECUTABLE={sys.executable}", f"-DSNAPPAD_GENERATED_ROOT={generated}",
                    f"-DSNAPPAD_RECUT_ROOT={source}", f"-DSNAPPAD_INPUTS_RECORD={receipt}"], check=True)
    subprocess.run(["cmake", "--build", str(build), "--parallel", str(args.jobs)], check=True)
    verify_inputs(generated, source, receipt)
    print(build / "SnapPadGame.dylib")


if __name__ == "__main__":
    main()
