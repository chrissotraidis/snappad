#!/usr/bin/env python3
"""Prove the SnapPad touch shell stays an intentional PaperPad adaptation."""

from __future__ import annotations

import difflib
import hashlib
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAPERPAD = ROOT / "ref/paperpad"


def common_substitutions(text: str) -> str:
    for source, destination in (
        ("PAPERPAD", "SNAPPAD"),
        ("PaperPad", "SnapPad"),
        ("paperpad", "snappad"),
        ("Paper Mario", "Pokémon Snap"),
        ("paper_mario", "pokemon_snap"),
    ):
        text = text.replace(source, destination)
    return text


def normalize_ios_main(text: str) -> str:
    text = common_substitutions(text)
    # SnapPad exposes RT64's genuine expanded projection separately from the
    # PaperPad-derived final-composite Fill crop. It is default-off and labeled
    # experimental because Pokémon Snap's photo/scoring path is 4:3-authored.
    text = text.replace(
        "    return MAX(0, MIN(4, resolution));\n}\n\n} // namespace",
        "    return MAX(0, MIN(4, resolution));\n}\n\n"
        "NSInteger aspectModeFromSettings(NSDictionary* settings) {\n"
        "    NSInteger aspect = settings[@\"aspect\"] == nil\n"
        "        ? 0 : [settings[@\"aspect\"] integerValue];\n"
        "    return MAX(0, MIN(2, aspect));\n"
        "}\n\n} // namespace",
    )
    text = text.replace(
        '    _aspectControl = [[UISegmentedControl alloc] initWithItems:@[@"Original (4:3)", @"Fill Screen"]];\n',
        '    _aspectControl = [[UISegmentedControl alloc]\n'
        '        initWithItems:@[@"Original (4:3)", @"Fill Screen", @"Wide (Experimental)"]];\n',
    )
    text = text.replace(
        "    [stack addArrangedSubview:_aspectControl];\n\n    // Touch controls.",
        "    [stack addArrangedSubview:_aspectControl];\n"
        "    UILabel* aspectNote = [self label:\n"
        "        @\"Wide expands the 3D field of view. Pokémon Snap's reticle, photographs, and scoring were designed for 4:3; use Original for accurate play.\"];\n"
        "    aspectNote.font = [UIFont systemFontOfSize:14.0];\n"
        "    aspectNote.textColor = [UIColor colorWithWhite:0.72 alpha:1.0];\n"
        "    aspectNote.numberOfLines = 3;\n"
        "    [stack addArrangedSubview:aspectNote];\n\n"
        "    // Touch controls.",
    )
    text = text.replace(
        '    int aspect = saved[@"aspect"] ? [saved[@"aspect"] intValue] : 0;',
        "    NSInteger aspect = aspectModeFromSettings(saved);",
    )
    text = text.replace(
        '            int aspect = settings[@"aspect"] ? [settings[@"aspect"] intValue] : 0;',
        "            NSInteger aspect = aspectModeFromSettings(settings);",
    )
    text = text.replace(
        "            SnapPad_SetGraphicsConfig(static_cast<int>(resolution), aspect, 0);",
        "            SnapPad_SetGraphicsConfig(\n"
        "                static_cast<int>(resolution), static_cast<int>(aspect), 0);",
    )
    # PaperPad's non-release autoboot is a Paper Mario/PSR test seam, not a
    # game-neutral UI mechanism and not valid for Pokémon Snap.
    text = text.replace(
        '#if !defined(SNAPPAD_RELEASE_BUILD)\n'
        '        setenv("PSR_AUTOBOOT", "1", 1);\n'
        '#endif\n\n',
        "",
    )
    # PaperPad's target tolerates a six-poll released-button latch. Pokémon
    # Snap can consume that as multiple name/menu actions. Preserve the latch
    # mechanism as a one-sample edge and keep only action buttons out of the
    # raw held-button path; Z/directions/shoulders retain true holds.
    text = text.replace(
        "constexpr uint8_t kTapHoldPolls = 6;",
        "// PaperPad's six-poll tap latch is too long for Pokémon Snap's name and menu\n"
        "// readers: one released A tap can span two updates and enter the same character\n"
        "// twice. One native poll preserves the edge without manufacturing a hold.\n"
        "constexpr uint8_t kTapHoldPolls = 1;\n"
        "// Pokémon Snap treats A and Start as actions in the accepted name/menu/camera\n"
        "// paths, while B, Z, and the directional/shoulder controls retain PaperPad's\n"
        "// true hold behavior. Publishing A/Start only through the edge latch makes a\n"
        "// physical tap exactly one N64 sample and keeps Z+A camera multi-touch usable.\n"
        "constexpr uint16_t kPulseButtonMask = 0x8000 | 0x1000;",
    )
    text = text.replace(
        "        } else {\n"
        "            buttons |= control.mask;\n"
        "        }\n"
        "    }\n"
        "    g_touch_buttons.store(buttons, std::memory_order_relaxed);",
        "        } else if ((control.mask & kPulseButtonMask) == 0) {\n"
        "            buttons |= control.mask;\n"
        "        }\n"
        "    }\n"
        "    g_touch_buttons.store(buttons, std::memory_order_relaxed);",
    )
    # SnapPad's verified core updates N64 input at 30 Hz under a roughly 60 Hz
    # native bridge. Preserve PaperPad's bounded flick-latch mechanism, but
    # require two polls so a quick released flick crosses one complete game
    # update instead of occasionally disappearing between updates.
    text = text.replace(
        "// Preserve a very short released flick for one runtime poll. Replaying it for\n"
        "// several polls makes grid/name-entry selectors overshoot after the thumb has\n"
        "// already returned to neutral.\n"
        "constexpr uint8_t kAnalogFlickHoldPolls = 1;",
        "// Preserve a very short released flick across one complete 30 Hz game update.\n"
        "// The native bridge is polled near 60 Hz, so a one-poll latch can disappear\n"
        "// between Pokémon Snap's menu updates. Two polls guarantee one observed edge\n"
        "// without the repeated grid/name-entry movement caused by a longer replay.\n"
        "constexpr uint8_t kAnalogFlickHoldPolls = 2;",
    )
    return text


def normalize_rom_setup(text: str) -> str:
    text = common_substitutions(text)
    replacements = (
        ("40u * 1024u * 1024u", "16u * 1024u * 1024u"),
        ("// Pokémon Snap (US) 1.0 normalized big-endian sha1.",
         "// Pokémon Snap (US) normalized big-endian SHA-1."),
        ("3837f44cda784b466c9a2d99df70d77c322b97a0",
         "edc7c49cc568c045fe48be0d18011c30f393cbaf"),
        ("not 40 MiB", "not 16 MiB"),
        ("Pokémon Snap (US) 1.0 ROM", "Pokémon Snap (US) ROM"),
        ("SnapPad supports Pokémon Snap (US) 1.0 only.",
         "SnapPad supports the Pokémon Snap US revision only."),
        ("Pokémon Snap US 1.0", "Pokémon Snap US"),
        ("Supported revision: US 1.0", "Supported revision: US"),
        ("papermario.us.1.0.z64", "pokemonsnap.n64.us.z64"),
    )
    for source, destination in replacements:
        text = text.replace(source, destination)
    # iOS 26's document picker can leave a landscape-only app's Simulator
    # scene in portrait, and an immediate result alert can be attached to the
    # picker while UIKit is dismissing it. Require SnapPad's post-picker scene
    # restoration and delayed result presentation as audited shell hardening.
    text = text.replace(
        "void styleButton(UIButton* button) {",
        "UIWindowScene* foregroundWindowScene() {\n"
        "    UIWindowScene* fallback = nil;\n"
        "    for (UIScene* scene in UIApplication.sharedApplication.connectedScenes) {\n"
        "        if (![scene isKindOfClass:UIWindowScene.class]) continue;\n"
        "        UIWindowScene* windowScene = static_cast<UIWindowScene*>(scene);\n"
        "        if (scene.activationState == UISceneActivationStateForegroundActive) {\n"
        "            return windowScene;\n"
        "        }\n"
        "        if (fallback == nil &&\n"
        "            scene.activationState == UISceneActivationStateForegroundInactive) {\n"
        "            fallback = windowScene;\n"
        "        }\n"
        "    }\n"
        "    return fallback;\n"
        "}\n\n"
        "void restoreLandscapeOrientation(UIViewController* presenter) {\n"
        "    if (presenter == nil) return;\n"
        "    dispatch_async(dispatch_get_main_queue(), ^{\n"
        "        if (@available(iOS 16.0, *)) {\n"
        "            [presenter setNeedsUpdateOfSupportedInterfaceOrientations];\n"
        "            UIWindowScene* scene = presenter.view.window.windowScene;\n"
        "            if (scene != nil) {\n"
        "                UIWindowSceneGeometryPreferencesIOS* preferences =\n"
        "                    [[UIWindowSceneGeometryPreferencesIOS alloc]\n"
        "                        initWithInterfaceOrientations:UIInterfaceOrientationMaskLandscape];\n"
        "                [scene requestGeometryUpdateWithPreferences:preferences\n"
        "                    errorHandler:^(__unused NSError* geometryError) {}];\n"
        "            }\n"
        "        } else {\n"
        "            [UIViewController attemptRotationToDeviceOrientation];\n"
        "        }\n"
        "    });\n"
        "}\n\n"
        "void styleButton(UIButton* button) {",
    )
    text = text.replace(
        "        self.imported = YES;\n"
        "        return;",
        "        self.imported = YES;\n"
        "        restoreLandscapeOrientation(self);\n"
        "        return;",
    )
    text = text.replace(
        "    self.statusLabel.text = error.localizedDescription ?: @\"SnapPad could not import that file.\";\n"
        "}",
        "    self.statusLabel.text = error.localizedDescription ?: @\"SnapPad could not import that file.\";\n"
        "    [self.view.window makeKeyAndVisible];\n"
        "    restoreLandscapeOrientation(self);\n"
        "}",
        1,
    )
    text = text.replace(
        "    self.statusLabel.text = @\"No ROM selected. Choose your legal copy whenever you're ready.\";\n"
        "}",
        "    self.statusLabel.text = @\"No ROM selected. Choose your legal copy whenever you're ready.\";\n"
        "    [self.view.window makeKeyAndVisible];\n"
        "    restoreLandscapeOrientation(self);\n"
        "}",
        1,
    )
    text = text.replace(
        "    SnapPadROMSetupController* controller = [[SnapPadROMSetupController alloc] init];\n"
        "    UIWindow* window = [[UIWindow alloc] initWithFrame:UIScreen.mainScreen.bounds];",
        "    UIWindowScene* scene = foregroundWindowScene();\n"
        "    if (scene == nil) {\n"
        "        std::fprintf(stderr, \"[SnapPad] setup window scene unavailable\\n\");\n"
        "        return false;\n"
        "    }\n\n"
        "    SnapPadROMSetupController* controller = [[SnapPadROMSetupController alloc] init];\n"
        "    UIWindow* window = [[UIWindow alloc] initWithWindowScene:scene];\n"
        "    window.frame = scene.coordinateSpace.bounds;",
    )
    old_manager_delegate = """- (void)documentPicker:(UIDocumentPickerViewController*)controller
didPickDocumentsAtURLs:(NSArray<NSURL*>*)urls {
    NSError* error = nil;
    if (urls.count == 1 && installROMFromURL(urls.firstObject, &error)) {
        [self showMessage:@\"ROM Verified\"
                     body:@\"The private copy was replaced. Relaunch SnapPad when you want the running game to use it.\"];
        return;
    }
    [self showMessage:@\"ROM Not Imported\"
                 body:error.localizedDescription ?: @\"SnapPad could not import that file.\"];
}
"""
    new_manager_delegate = """- (void)documentPicker:(UIDocumentPickerViewController*)controller
didPickDocumentsAtURLs:(NSArray<NSURL*>*)urls {
    NSError* error = nil;
    NSString* title = nil;
    NSString* body = nil;
    if (urls.count == 1 && installROMFromURL(urls.firstObject, &error)) {
        title = @\"ROM Verified\";
        body = @\"The private copy was replaced. Relaunch SnapPad when you want the running game to use it.\";
    } else {
        title = @\"ROM Not Imported\";
        body = error.localizedDescription ?: @\"SnapPad could not import that file.\";
    }
    restoreLandscapeOrientation(self.presenter);
    // UIDocumentPicker dismisses itself after the delegate callback. Wait for
    // that transition before presenting the result so the alert is not attached
    // to a picker that UIKit is removing.
    dispatch_after(dispatch_time(DISPATCH_TIME_NOW, 350 * NSEC_PER_MSEC),
                   dispatch_get_main_queue(), ^{
        [self showMessage:title body:body];
    });
}

- (void)documentPickerWasCancelled:(UIDocumentPickerViewController*)controller {
    restoreLandscapeOrientation(self.presenter);
}
"""
    text = text.replace(old_manager_delegate, new_manager_delegate)
    return text


def normalize_diagnostics(text: str) -> str:
    text = common_substitutions(text)
    text = text.replace(
        '#include "snappad_input.h"\n',
        '#include "gyro_input_policy.h"\n#include "snappad_input.h"\n',
    )
    # Diagnostics must describe SnapPad's exact supported 16 MiB input rather
    # than inheriting Paper Mario's 40 MiB size test.
    text = text.replace(
        "40ull * 1024ull * 1024ull",
        "16ull * 1024ull * 1024ull",
    )
    text = text.replace(
        '    [report appendFormat:@"Aspect ratio: %@\\n",\n'
        '        [settings[@"aspect"] integerValue] == 1 ? @"Fill Screen" : @"Original (4:3)"];',
        '    const NSInteger aspect = [settings[@"aspect"] integerValue];\n'
        '    NSString* aspectName = @"Original (4:3)";\n'
        '    if (aspect == 1) {\n'
        '        aspectName = @"Fill Screen";\n'
        '    } else if (aspect == 2) {\n'
        '        aspectName = @"Wide (Experimental)";\n'
        '    }\n'
        '    [report appendFormat:@"Aspect ratio: %@\\n", aspectName];',
    )
    return text.replace(
        '    [report appendFormat:@"Touch opacity: %.0f%%\\n", opacity * 100.0];\n',
        '    [report appendFormat:@"Touch opacity: %.0f%%\\n", opacity * 100.0];\n'
        '    [report appendFormat:@"Gyro controls enabled: %@\\n",\n'
        '        yesNo([settings[@"gyroControls"] boolValue])];\n'
        '    const double gyroSensitivity = settings[@"gyroSensitivity"] == nil\n'
        '        ? snappad::kDefaultGyroSensitivity\n'
        '        : [settings[@"gyroSensitivity"] doubleValue];\n'
        '    [report appendFormat:@"Gyro sensitivity: %.0f%%\\n", gyroSensitivity * 100.0];\n'
        '    [report appendFormat:@"Gyro horizontal inverted: %@\\n",\n'
        '        yesNo(settings[@"gyroInvertHorizontal"] == nil\n'
        '            ? snappad::kDefaultGyroInvertHorizontal\n'
        '            : [settings[@"gyroInvertHorizontal"] boolValue])];\n'
        '    [report appendFormat:@"Gyro vertical inverted: %@\\n",\n'
        '        yesNo(settings[@"gyroInvertVertical"] == nil\n'
        '            ? snappad::kDefaultGyroInvertVertical\n'
        '            : [settings[@"gyroInvertVertical"] boolValue])];\n',
    )


def normalize_info_plist(text: str) -> str:
    text = common_substitutions(text)
    return text.replace(
        '    <key>LSRequiresIPhoneOS</key>\n'
        '    <true/>\n',
        '    <key>LSRequiresIPhoneOS</key>\n'
        '    <true/>\n'
        '    <key>NSMotionUsageDescription</key>\n'
        '    <string>SnapPad uses device motion only while you enable gyro camera controls.</string>\n',
    )


def normalize_touch_latch(text: str) -> str:
    text = text.replace(
        "class PaperPadTouchTapLatch {",
        "// Ported directly from PaperPad's proven touch edge/latch mechanism. A quick\n"
        "// tap remains visible for a bounded number of runtime polls, while clearAll()\n"
        "// guarantees native UI and lifecycle transitions cannot leave held input.\n"
        "class SnapPadTouchTapLatch {",
    )
    return text.rstrip() + "\n"


def assert_equal(label: str, expected: str, actual: str) -> None:
    expected = expected.rstrip() + "\n"
    actual = actual.rstrip() + "\n"
    if expected == actual:
        return
    difference = "\n".join(
        difflib.unified_diff(
            expected.splitlines(),
            actual.splitlines(),
            fromfile=f"normalized PaperPad {label}",
            tofile=f"SnapPad {label}",
            n=3,
        )
    )
    raise SystemExit(f"error: unintended PaperPad shell drift in {label}:\n{difference}")


# The substantial native gyro extension is easier to review as one pinned
# unified difference than as a long sequence of reverse-normalization rules.
IOS_MAIN_AUDITED_DIFF_SHA256 = (
    "1da56621b6458c0a582717173eaa90853bbef1ff92b46aa539d1c1defafc1757"
)


def assert_audited_ios_difference(expected: str, actual: str) -> None:
    difference = "\n".join(
        difflib.unified_diff(
            (expected.rstrip() + "\n").splitlines(),
            (actual.rstrip() + "\n").splitlines(),
            fromfile="normalized PaperPad ios_main.mm",
            tofile="SnapPad ios_main.mm",
            n=3,
        )
    )
    digest = hashlib.sha256(difference.encode("utf-8")).hexdigest()
    if digest != IOS_MAIN_AUDITED_DIFF_SHA256:
        raise SystemExit(
            "error: unintended PaperPad shell drift in ios_main.mm "
            f"(audited diff SHA-256 {digest}):\n{difference}"
        )


def main() -> None:
    revision = subprocess.run(
        ["git", "-C", str(PAPERPAD), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if revision != "74b6e45830a06c7f274c5ac1ddd7c625bc13a557":
        raise SystemExit(f"error: PaperPad parity pin changed: {revision}")

    assert_audited_ios_difference(
        normalize_ios_main(
            (PAPERPAD / "apple/app/ios_main.mm").read_text(encoding="utf-8")
        ),
        (ROOT / "port/apple/ios_main.mm").read_text(encoding="utf-8"),
    )

    checks = (
        (
            "rom_setup.mm",
            PAPERPAD / "apple/app/rom_setup.mm",
            ROOT / "port/apple/rom_setup.mm",
            normalize_rom_setup,
        ),
        (
            "diagnostics.mm",
            PAPERPAD / "apple/app/diagnostics.mm",
            ROOT / "port/apple/diagnostics.mm",
            normalize_diagnostics,
        ),
        (
            "touch_tap_latch.h",
            PAPERPAD / "apple/app/touch_tap_latch.h",
            ROOT / "port/apple/touch_tap_latch.h",
            normalize_touch_latch,
        ),
        (
            "Info.plist.in",
            PAPERPAD / "apple/app/Info.plist.in",
            ROOT / "port/apple/Info.plist.in",
            normalize_info_plist,
        ),
        (
            "PrivacyInfo.xcprivacy",
            PAPERPAD / "apple/app/PrivacyInfo.xcprivacy",
            ROOT / "port/apple/PrivacyInfo.xcprivacy",
            lambda text: text,
        ),
    )
    for label, source, destination, transform in checks:
        assert_equal(
            label,
            transform(source.read_text(encoding="utf-8")),
            destination.read_text(encoding="utf-8"),
        )
    print(
        "PaperPad shell parity passed: six UI/lifecycle/privacy sources differ "
        "only by audited SnapPad substitutions."
    )


if __name__ == "__main__":
    main()
