# SnapPad Preview 2

Preview 2 adds native gyro camera controls for iPhone and iPad while retaining
the stable v0.1.0 game, save, rendering, audio, touch, and controller paths.

## Included

- Opt-in gyro enablement in the three-dot menu
- A movable and resizable **GYRO OFF/ON** gameplay control
- Gyro camera input that replaces the analog camera stick only while active
- 50–250% sensitivity under **SnapPad Settings → Gyro**
- Independent horizontal and vertical inversion
- Physically accepted defaults: 190% sensitivity, horizontal inversion off,
  vertical inversion on
- Motion input neutralization for menus, layout editing, backgrounding,
  controller handoff, and touch-control disablement
- Gyro settings in the privacy-bounded diagnostics report

The candidate was accepted as stable by the maintainer after hands-on gyro
play on a physical 12.9-inch iPad Pro running iPadOS 26.6. The in-place update
preserved the private ROM, FlashRAM saves, preferences, and touch layout.

## Download and install

`SnapPad-v0.2.0-preview.2-unsigned.ipa` is an unsigned, ARM64, ROM-free IPA for
iOS and iPadOS 15 or newer. Re-sign it with AltStore Classic plus AltServer, or
another compatible sideloading tool. It is not an App Store or TestFlight build
and does not require JIT.

You must supply your own legally obtained, unmodified Pokémon Snap (USA) ROM.
No ROM or game data is included or downloaded.

IPA SHA-256:
`f2d14409a8b342f1e24f388251eb52b0e354603139991068edfdefb336168efb`

Read the [installation and update guide](https://github.com/chrissotraidis/snappad/blob/main/docs/INSTALL_IPA.md)
before installing. Install Preview 2 over an existing SnapPad installation to
preserve its private app container; do not delete the app first.

## Known limits

- Dedicated physical-iPhone, wider controller/interruption, thermal, and long
  mobile-soak coverage remains ongoing.
- Full progression through every course, report, album, gallery, Rainbow
  Cloud, and credits is not yet comprehensively accepted.
- A visible opening terrain seam remains under investigation.
- Wide remains experimental because photo capture and scoring are authored
  around the original 4:3 presentation.

SnapPad is unofficial and is not affiliated with Nintendo, The Pokémon
Company, or their partners. The upstream decompilation and translated-code
rights boundary remains unresolved. See `RIGHTS_AND_LICENSES.md` before
redistributing or expanding the release scope.
