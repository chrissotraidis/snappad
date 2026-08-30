# SnapPad physical-device acceptance

Use this handoff on the Mac that has the physical iPhone or iPad. It preserves
the installed SnapPad data container and keeps Simulator evidence separate from
device evidence.

## Prerequisites

- Current SnapPad checkout on Apple Silicon with the private generated inputs.
- Xcode 26.x, an Apple Development identity, and the matching team identifier.
- One paired, unlocked iPhone or iPad with Developer Mode enabled.
- The user's own verified Pokémon Snap US ROM available through Files.

Do not uninstall SnapPad from a device that contains its private ROM, settings,
or save. The deployment helper performs an in-place install and never removes
the application container.

Before every later physical-device update, copy these paths from the existing
`com.chrissotraidis.snappad` app data container into an ignored
`artifacts/device-backups/` directory:

- `Library/Application Support/SnapPad`
- `Library/Preferences/com.chrissotraidis.snappad.plist`
- `Documents`, when present

Record hashes for the ROM, preferences, and save payloads before installation,
install in place, then read them back and compare. Logs and active-session
markers can change normally and are not preservation hashes. Never use
`--remove-existing-content`, change the bundle identifier, or uninstall the
accepted app unless an explicit reset has been authorized.

## Build, audit, install, and launch

```sh
export SNAPPAD_APPLE_TEAM_ID=YOUR_TEAM_ID
scripts/check-ios-device-readiness.sh
scripts/build-ios-device.sh --signed
xcrun devicectl list devices
scripts/deploy-ios-device.sh --device DEVICE_ID
```

The build must report an ARM64, iOS 15+, AOT-only, ROM-free signed bundle. Save
the executable SHA-256 printed by the deployment helper. A successful build,
install, launch, or PID is not hands-on acceptance.

## Baseline hands-on pass

Run Original (4:3) first on one device at a time:

1. Confirm native first-run ROM selection or retained private ROM recognition.
2. Reach title, Continue/new game, Oak's Lab, and Beach using touch.
3. Hold Z and tap A simultaneously; confirm exactly one photograph is stored.
4. Complete photo review, submit a plausible score, save, terminate, relaunch,
   and Continue without data loss.
5. Move and reset the touch layout; check phone/tablet safe areas and comfortable
   two-thumb reach.
6. Enable gyro from `•••`, move and resize the on-screen gyro toggle, then verify
   both landscape orientations: **GYRO ON** must replace analog camera input with
   correctly directed device motion, and **GYRO OFF** must restore the analog
   stick without drift or a stuck axis.
   In **Settings → Gyro**, verify the accepted 190% default is responsive,
   vertical inversion defaults on, horizontal inversion defaults off, the
   sensitivity slider changes camera speed, and each inversion switch affects
   only its named axis.
7. Background for at least ten seconds and foreground; confirm rendering, input,
   and audio resume without a stuck control or queued-audio burst.
8. Connect a controller during gameplay; confirm touch targets hide, gyro pauses,
   the menu remains available, P1 mappings work, and touch/gyro return after
   disconnect.
9. Exercise a real audio interruption, then continue gameplay.
10. Play a focused course band and a sustained session while observing cadence,
   audio continuity, temperature, memory pressure, and battery behavior.

Record the device model, OS version, source revision, executable SHA-256,
signing team/profile identity, start/end time, settings, and any defect. Export
SnapPad diagnostics only after reviewing the privacy-bounded text.

## Current physical baseline

On 2026-08-28, the current signed candidate was installed for the first time on
an iPad Pro 12.9-inch (6th generation) running iPadOS 26.6. The normalized ROM
was written to the new private container with owner-only permissions and read
back with the locked Pokémon Snap US SHA-1. SnapPad remained running; its local
log confirmed the registered game core, a native 2732×2048 Metal drawable, the
verified audio RSP path, and live touch input.

The initial private Application Support and preferences baseline is retained
under ignored `artifacts/device-backups/2026-08-28-initial/`. This is deployment
and early runtime evidence, not completion of the hands-on checklist above.

## Experimental widescreen pass

After the baseline passes, select **Wide (Experimental)** and verify that Beach
shows additional horizontal 3D scene content rather than a crop. Then test the
reticle, Z+A shutter, stored photograph, Camera Check thumbnail, subject
detection, Oak score, and save/reload. Any disagreement with Original keeps Wide
experimental; it does not block the baseline candidate. Restore Original when
finished.
