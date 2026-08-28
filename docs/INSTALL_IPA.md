# Install SnapPad on iPhone or iPad

SnapPad v0.1.0 is published as an **unsigned, ROM-free IPA** for iOS and iPadOS
15 or newer. It is not an App Store or TestFlight build. A sideloading tool
must re-sign it for your device before installation.

- [Download `SnapPad-v0.1.0-unsigned.ipa`](https://github.com/chrissotraidis/snappad/releases/download/v0.1.0/SnapPad-v0.1.0-unsigned.ipa)
- [Download the SHA-256 checksum](https://github.com/chrissotraidis/snappad/releases/download/v0.1.0/SnapPad-v0.1.0-unsigned.ipa.sha256)
- Expected IPA SHA-256: `37741aebff29f05263cee6a7fb146b3f76c5c75c30ccd958caeb34e5a06590df`

The IPA contains no Pokémon Snap ROM or other game data. You must supply your
own legally obtained, unmodified Pokémon Snap (USA) ROM after installation.
SnapPad uses ahead-of-time ARM64 code and does not require JIT.

## Install with AltStore Classic

1. Install **AltStore Classic** and AltServer using the official
   [macOS guide](https://faq.altstore.io/altstore-classic/how-to-install-altstore-macos)
   or [Windows guide](https://faq.altstore.io/altstore-classic/how-to-install-altstore-windows).
2. Connect and trust your iPhone or iPad. On iOS or iPadOS 16 and later, enable
   **Settings → Privacy & Security → Developer Mode**.
3. Download the SnapPad IPA above and save it to Files.
4. Keep AltServer running. Open AltStore Classic, choose **My Apps**, tap **+**,
   select the IPA, and wait for AltStore to sign and install it.
5. Launch SnapPad, tap **Choose ROM**, and select your supported ROM through
   Apple's Files picker.

AltStore PAL is a different distribution channel and cannot import arbitrary
unsigned IPA files. Another sideloading tool may work if it can correctly
re-sign a standard unsigned IPA, but AltStore Classic is the documented path.

## Refresh and update

Apps signed with a free Apple ID expire after seven days. AltStore Classic can
refresh them while AltServer is available, and free accounts normally allow
three active sideloaded apps.

To update SnapPad without losing its private ROM, saves, or settings:

1. Download the newer IPA.
2. Install it over the existing SnapPad app using the same Apple ID and
   sideloading tool.
3. Do **not** delete SnapPad first.

Back up important saves before any sideloaded update. In-place replacement is
the supported update path, but third-party signing tools can still expire or
replace an app container outside SnapPad's control.

## If installation fails

- Confirm you downloaded the complete `.ipa`, not the checksum file.
- Confirm you are using AltStore Classic with AltServer, not AltStore PAL.
- Unlock and trust the device, and confirm Developer Mode is enabled.
- Keep AltServer running on the same Wi-Fi network or connect the device by USB.
- Verify the downloaded IPA against the SHA-256 value above.
