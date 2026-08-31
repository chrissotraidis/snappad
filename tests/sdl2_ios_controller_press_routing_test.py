#!/usr/bin/env python3
"""Keep iOS gamepad presses out of SnapPad's keyboard Start binding."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "ref/SDL2/src/video/uikit/SDL_uikitview.m"


def main() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    function_start = source.index("- (SDL_Scancode)scancodeFromPress:")
    function_end = source.index("- (void)pressesBegan:", function_start)
    function = source[function_start:function_end]

    keyboard_path = "return (SDL_Scancode)press.key.keyCode;"
    tv_guard = "#if TARGET_OS_TV\n#ifndef SDL_JOYSTICK_DISABLED"
    select_path = "case UIPressTypeSelect:"
    if keyboard_path not in function:
        raise SystemExit("physical-keyboard scancode routing was removed")
    if tv_guard not in function:
        raise SystemExit("controller-style UIKit presses are not restricted to tvOS")
    if function.index(tv_guard) > function.index(select_path):
        raise SystemExit("UIPressTypeSelect remains outside the tvOS guard")
    print("sdl2_ios_controller_press_routing_test: iOS controller/keyboard routes separated")


if __name__ == "__main__":
    main()
