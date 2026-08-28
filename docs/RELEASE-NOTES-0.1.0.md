# SnapPad v0.1.0

The first public SnapPad release brings Pokémon Snap to iPhone, iPad, and Apple
Silicon Mac through ahead-of-time static recompilation and native Metal
rendering.

## Included

- Complete customizable N64 touch controls for iPhone and iPad
- SDL-compatible physical-controller support
- Native Files-based ROM selection, exact revision validation, and private
  on-device storage
- Persistent FlashRAM saves and settings
- Original 4:3, Fill Screen, and default-off Wide (Experimental) presentation
- Native diagnostics, lifecycle handling, and data-preserving update support
- iPhone and iPad app icons plus the required privacy manifest

The release candidate was accepted as stable by the maintainer after hands-on
play on a physical 12.9-inch iPad Pro running iPadOS 26.6.

## Download and install

`SnapPad-v0.1.0-unsigned.ipa` is an unsigned, ARM64, ROM-free IPA for iOS and
iPadOS 15 or newer. Re-sign it with AltStore Classic plus AltServer, or another
compatible sideloading tool. It is not an App Store or TestFlight build and
does not require JIT.

You must supply your own legally obtained, unmodified Pokémon Snap (USA) ROM
after installation. No ROM or game data is included or downloaded.

IPA SHA-256:
`37741aebff29f05263cee6a7fb146b3f76c5c75c30ccd958caeb34e5a06590df`

Read the [installation and update guide](https://github.com/chrissotraidis/snappad/blob/main/docs/INSTALL_IPA.md) before installing.

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
