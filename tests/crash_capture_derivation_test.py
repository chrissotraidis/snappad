#!/usr/bin/env python3
"""Keep crash evidence collection aligned with the pinned PaperPad mechanism."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    reference = (ROOT / "ref/paperpad/scripts/capture-crashes.sh").read_text(
        encoding="utf-8"
    )
    actual = (ROOT / "scripts/capture-crashes.sh").read_text(encoding="utf-8")
    expected = reference.replace("PaperPad", "SnapPad")
    # Use bash's read builtin rather than spawning cat for the one marker read.
    expected = expected.replace('LAST="$(cat "$MARKER")"', 'LAST="$(<"$MARKER")"')
    if actual != expected:
        raise SystemExit("SnapPad crash collector drifted from pinned PaperPad")
    print("crash_capture_derivation_test: exact audited SnapPad substitution")


if __name__ == "__main__":
    main()
