#!/usr/bin/env python3
"""Keep the unmeasured renderer baseline free of Paper Mario carryover."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "port/runtime/snappad_rt64_context.cpp"
RUNNER = ROOT / "port/runtime/snappad_runner.cpp"
IOS_SHELL = ROOT / "port/apple/ios_main.mm"


def main() -> None:
    text = SOURCE.read_text(encoding="utf-8")
    forbidden = {
        "paper_mario": "Paper Mario namespace",
        "PAPERPAD_": "PaperPad diagnostic variable",
        "forceBranch = true": "forced F3DEX branch enhancement",
        "textureLOD.scale = true": "forced texture-LOD enhancement",
        "DisplayBuffering::Triple": "PaperPad triple-buffer override",
        "idleWorkActive = false": "PaperPad idle-work override",
    }
    for token, label in forbidden.items():
        if token in text:
            raise SystemExit(f"renderer policy inherited {label}: {token}")

    required = (
        "const bool wide_projection =",
        "? RT64::UserConfiguration::AspectRatio::Expand",
        "config.ar_option == ultramodern::renderer::AspectRatio::Expand;",
        "app->userConfig.refreshRate = RT64::UserConfiguration::RefreshRate::Original;",
        "SNAPPAD_DL_HASH",
        "SNAPPAD_ORIGIN_BURST",
        "pokemon_snap::renderer::create_render_context",
    )
    for token in required:
        if token not in text:
            raise SystemExit(f"renderer baseline contract disappeared: {token}")
    runner = RUNNER.read_text(encoding="utf-8")
    shell = IOS_SHELL.read_text(encoding="utf-8")
    if "aspect_mode == 2" not in runner or "AspectRatio::Manual" not in runner:
        raise SystemExit("experimental wide mode no longer maps to its distinct runtime signal")
    if '@"Wide (Experimental)"' not in shell or "aspectModeFromSettings" not in shell:
        raise SystemExit("experimental wide mode lost its labeled, bounded native setting")
    print("renderer_policy_test: original baseline plus explicit experimental wide projection")


if __name__ == "__main__":
    main()
