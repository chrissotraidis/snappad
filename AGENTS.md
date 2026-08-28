# SnapPad workspace instructions

Keep the accepted physical-device installation state intact during iteration.

- Keep the bundle identifier `com.chrissotraidis.snappad` stable.
- Never uninstall SnapPad, erase its container, or use
  `--remove-existing-content` unless the user explicitly authorizes a reset.
- Before every physical-device update, copy the current SnapPad Application
  Support data, preferences plist, and Documents data into an ignored
  `artifacts/device-backups/` directory.
- Install updates in place with `scripts/deploy-ios-device.sh`. Afterward,
  verify that the private ROM, saves, and preferences are still present before
  claiming the update preserved state.
- Rediscover the target device and obtain the signing team from the selected
  provisioning profile's `TeamIdentifier`; do not hardcode device identifiers
  or infer the team from a certificate's display name.
- ROMs, saves, preferences backups, signing material, and generated artifacts
  remain private and must never be staged or published.
