# SnapPad release readiness

Status: **GO for the free v0.1.0 source snapshot and unsigned ROM-free IPA**.
Last reviewed: 2026-08-28

The maintainer accepted the current physical-iPad build as stable and
explicitly authorized the first source snapshot and unsigned GitHub IPA. The
release remains unofficial, source-available, ROM-free, and outside App Store
or TestFlight distribution. Broader compatibility work and the upstream
translated-code rights uncertainty remain documented rather than hidden. See
`docs/RIGHTS-STATUS.md` and `RIGHTS_AND_LICENSES.md`.

## Completed public-facing preparation

- A production 1024×1024 opaque icon is wired through the shared iOS/iPadOS
  asset catalog. The current build emits and audits the iPhone and iPad icon
  variants plus `Assets.car`.
- The README now leads with current gameplay, states install availability in
  consumer terms, explains the exact supported ROM, and keeps Simulator,
  physical-device, and public-distribution claims separate.
- On 2026-08-28, the current ROM-free candidate built and passed its ARM64 iOS
  Simulator bundle audit, installed on iPad Pro 11-inch and 13-inch (M5)
  Simulators with iOS 26.5, launched the private supported ROM, rendered the
  title sequence, and accepted the on-screen Start input into the New
  Game/Options menu.
- The same pass found and repaired a first-run lifecycle defect: cancelling the
  Files picker could leave SnapPad's scene behind the previously active app.
  The setup window is now attached to the foreground `UIWindowScene`; an
  isolated iPad Simulator recheck remained in SnapPad, restored landscape,
  displayed a retry message, and reopened Files successfully.
- The current candidate also built as a development-signed ARM64 `iphoneos`
  application and passed the ROM-free device-bundle, privacy-manifest,
  architecture, runtime-dependency, personal-path, credential, signature,
  profile, and iPhone/iPad icon audits.
- On 2026-08-28, it was installed for the first time on an iPad Pro 12.9-inch
  (6th generation) running iPadOS 26.6. The private normalized ROM was copied
  into the new app container, read back with the locked SHA-1 and owner-only
  permissions, and recognized at launch. Device-local logs confirmed the game
  core, native Metal window, verified audio RSP route, and live touch input.
  The initial private container baseline is backed up under ignored artifacts.
- The repository safety audit rejects tracked game data, generated AOT output,
  packages, signing material, likely credentials, personal paths, and oversized
  files.
- The public packaging path requires an unsigned ARM64 iPhoneOS app, strips no
  signed release into existence, includes the scoped rights notice and pinned
  dependency license files, rejects game/signing/private data, and emits a
  separately audited checksum.

## v0.1.0 release record

- Tag: `v0.1.0`
- App version/build: `0.1.0` (`1`)
- Platforms: iOS and iPadOS 15 or newer; ARM64; iPhone and iPad families
- Artifact: `SnapPad-v0.1.0-unsigned.ipa`
- IPA SHA-256: `37741aebff29f05263cee6a7fb146b3f76c5c75c30ccd958caeb34e5a06590df`
- IPA size: `7,699,951 bytes`
- Signing: unsigned and re-signable; no provisioning profile
- Game data: not included; user-supplied Pokémon Snap (USA) ROM required
- Distribution: free GitHub community release; not App Store or TestFlight

## Known post-release work

1. Complete dedicated physical-iPhone coverage and the wider physical-device
   controller, interruption, thermal, and long-soak matrix.
2. Complete the broader full-game progression
   pass; keep the known opening terrain seam explicit until resolved.
3. Verify each later IPA through the same build, package-twice, download-back,
   checksum, and in-place state-preservation flow.
4. Resolve the decompilation/static-translation rights boundary before any
   paid, commercial, TestFlight, App Store, or official-store distribution.
