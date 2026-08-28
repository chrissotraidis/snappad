#!/usr/bin/env python3
"""Require bounded diagnostics before the first real gameplay boot."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def require(path: str, marker: str) -> None:
    text = (ROOT / path).read_text(encoding="utf-8")
    if marker not in text:
        raise SystemExit(f"missing runtime breadcrumb {marker!r} in {path}")


def main() -> None:
    require("port/runtime/snappad_runner.cpp", "[core] registered Pokémon Snap US")
    require("port/runtime/snappad_runner.cpp", "[rsp] first audio task")
    require("port/runtime/register_overlays.cpp", "[overlay] registered sections=")
    require("port/runtime/snappad_game_hooks.cpp", "[dynamic-code] SP integrity failure")
    require("port/runtime/snappad_rt64_context.cpp", "[render] swapchain=")
    print("runtime_breadcrumb_contract_test: core/overlay/RSP/render/dynamic markers present")


if __name__ == "__main__":
    main()
