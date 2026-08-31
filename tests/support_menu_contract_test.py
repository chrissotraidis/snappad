#!/usr/bin/env python3
"""Keep diagnostics export and issue reporting discoverable in the iOS menu."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "port/apple/ios_main.mm"


def require(source: str, token: str) -> None:
    if token not in source:
        raise SystemExit(f"support menu contract missing: {token}")


def main() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    require(source, '@"Diagnostics & Support…"')
    require(source, '@"Export Diagnostics & Logs…"')
    require(source, "snappad_present_diagnostics_share")
    require(source, '@"Open GitHub Issues"')
    require(source, '@"https://github.com/chrissotraidis/snappad/issues"')
    print("support_menu_contract_test: export and issue-reporting actions present")


if __name__ == "__main__":
    main()
