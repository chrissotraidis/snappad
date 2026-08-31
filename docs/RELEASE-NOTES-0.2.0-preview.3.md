# SnapPad Preview 3

Preview 3 strengthens Pokémon Snap photo review, separates iOS controller
presses from keyboard Start input, and makes support tools easier to find.

## Included

- Photo-subject correlation at the game's accepted `makePhoto` event, covering
  the normal hold-Z shutter path without inferring a particular button chord
- A narrow SDL2 iOS routing patch that prevents controller-style UIKit Select
  presses from also becoming keyboard Return/Start
- **Diagnostics & Support…** in the three-dot menu
- **Export Diagnostics & Logs…** using the existing privacy-reviewed report
- **Open GitHub Issues** for direct access to SnapPad's issue tracker
- Regression contracts for photo correlation, controller routing, and support
  menu actions

The maintainer completed a hands-on pass on a physical 12.9-inch iPad Pro
running iPadOS 26.6. Holding Z and taking normal Beach photographs produced
selectable recognized Pokémon, Professor Oak accepted multiple species and
better reports, and the next course unlocked. The in-place update preserved
both private ROM copies, both FlashRAM save files, preferences, and layout data
byte-for-byte.

## Download and install

`SnapPad-v0.2.0-preview.3-unsigned.ipa` is an unsigned, ARM64, ROM-free IPA for
iOS and iPadOS 15 or newer. Re-sign it with AltStore Classic plus AltServer, or
another compatible sideloading tool. It is not an App Store or TestFlight build
and does not require JIT.

You must supply your own legally obtained, unmodified Pokémon Snap (USA) ROM.
No ROM or game data is included or downloaded.

IPA SHA-256:
`5bd09cc0c15baa02586f6ea9637346b90d49d19526768235306903992e1b1c16`

Install Preview 3 over an existing SnapPad installation to preserve its private
app container; do not delete the app first.

## Known limits

- The controller routing repair has automated and build coverage, but the
  reporter's PS5 and MCON controller models were not available for a physical
  reproduction. If A/Cross still pauses, export diagnostics immediately after
  reproducing it and attach the report to the GitHub issue.
- Dedicated physical-iPhone, interruption, thermal, and long mobile-soak
  coverage remains ongoing.
- Full progression through every course, report, album, gallery, Rainbow Cloud,
  and credits is not yet comprehensively accepted.
- Wide remains experimental because photo capture and scoring are authored
  around the original 4:3 presentation.

SnapPad is unofficial and is not affiliated with Nintendo, The Pokémon
Company, or their partners. The upstream decompilation and translated-code
rights boundary remains unresolved. See `RIGHTS_AND_LICENSES.md` before
redistributing or expanding the release scope.
