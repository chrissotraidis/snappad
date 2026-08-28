#!/usr/bin/env python3
"""Protect the applicable PaperPad README experience in SnapPad's README."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    required = {
        "status boundary": "## Current status",
        "supported input": "## Supported game input",
        "install path": "## Install on iPhone or iPad",
        "developer path": "## Build from source",
        "first launch": "## First launch",
        "touch/settings": "## Touch controls and settings",
        "bindings": "### Keyboard and controller bindings",
        "diagnostics": "## Diagnostics and bug reports",
        "ROM-free graph": "## Reproducible and private by construction",
        "FAQ": "## Frequently asked questions",
        "credits": "## Credits and design references",
        "rights": "## Legal and rights boundary",
    }
    for label, marker in required.items():
        if marker not in readme:
            raise SystemExit(f"README lost PaperPad-derived {label}: {marker}")
    for boundary in ("unsigned, ROM-free IPA", "never downloads game data", "one Simulator"):
        if boundary not in readme:
            raise SystemExit(f"README lost honest boundary: {boundary}")
    print("readme_paperpad_coverage_test: applicable PaperPad README structure retained")


if __name__ == "__main__":
    main()
