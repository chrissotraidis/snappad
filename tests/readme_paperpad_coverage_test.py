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
    for boundary in ("Public SnapPad binary downloads are paused", "never downloads game data", "one Simulator",
                     "there is no public SnapPad IPA", "On an Apple Silicon Mac with Xcode",
                     "Its old Preview 3 download links are retired"):
        if boundary not in readme:
            raise SystemExit(f"README lost honest boundary: {boundary}")
    for stale_claim in ("SnapPad Preview 3 release", "Preview 3 available",
                        "The GitHub release is an", "The first release is distributed"):
        if stale_claim in readme:
            raise SystemExit(f"README restored a retired download claim: {stale_claim}")
    guide = (ROOT / "docs/INSTALL_IPA.md").read_text(encoding="utf-8")
    for boundary in ("Public SnapPad binary downloads are paused",
                     "there is no current public SnapPad IPA", "existing PadMint recipe",
                     "Apple Silicon Mac with Xcode",
                     "Private source-build instructions",
                     "Do **not** delete SnapPad first."):
        if boundary not in guide:
            raise SystemExit(f"Install guide lost honest boundary: {boundary}")
    for stale_claim in ("SnapPad Preview 3 is published", "/releases/download/",
                        "Download the SnapPad IPA above", "Download the newer IPA"):
        if stale_claim in guide:
            raise SystemExit(f"Install guide restored a retired download claim: {stale_claim}")
    if "no current public SnapPad IPA or PadMint release recipe" in readme + guide:
        raise SystemExit("Documentation hides the existing personal Mac PadMint recipe")
    print("readme_paperpad_coverage_test: applicable PaperPad README structure retained")


if __name__ == "__main__":
    main()
