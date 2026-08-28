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
6. Background for at least ten seconds and foreground; confirm rendering, input,
   and audio resume without a stuck control or queued-audio burst.
7. Connect a controller during gameplay; confirm touch targets hide, the menu
   remains available, P1 mappings work, and touch returns after disconnect.
8. Exercise a real audio interruption, then continue gameplay.
9. Play a focused course band and a sustained session while observing cadence,
   audio continuity, temperature, memory pressure, and battery behavior.

Record the device model, OS version, source revision, executable SHA-256,
signing team/profile identity, start/end time, settings, and any defect. Export
SnapPad diagnostics only after reviewing the privacy-bounded text.

## Experimental widescreen pass

After the baseline passes, select **Wide (Experimental)** and verify that Beach
shows additional horizontal 3D scene content rather than a crop. Then test the
reticle, Z+A shutter, stored photograph, Camera Check thumbnail, subject
detection, Oak score, and save/reload. Any disagreement with Original keeps Wide
experimental; it does not block the baseline candidate. Restore Original when
finished.
