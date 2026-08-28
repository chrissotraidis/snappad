# SnapPad release checklist

Use this checklist for every public source snapshot and unsigned IPA.

- [ ] Set a deliberate semantic version and monotonically increasing build.
- [ ] Build the ARM64 `iphoneos` app with code signing disabled.
- [ ] Confirm the app and IPA target iOS 15 or newer and contain no signature
      or provisioning profile.
- [ ] Confirm the app and IPA contain no ROM, extracted game data, generated
      source input, saves, logs, signing material, credentials, or private path.
- [ ] Include `RIGHTS_AND_LICENSES.md` and discovered third-party notices.
- [ ] Package twice and require byte-identical IPA output.
- [ ] Run the full test suite, repository safety audit, shell syntax checks,
      package audit, and `git diff --check`.
- [ ] Record the release commit, tag, Xcode/SDK, app version/build, supported
      OS/device family, IPA filename, size, and SHA-256.
- [ ] Publish the unsigned IPA and checksum, download both, and verify the
      hosted IPA byte-for-byte against the audited local artifact.
- [ ] Confirm `main`, `origin/main`, the release tag, and the GitHub release all
      identify the intended source revision.

An unsigned IPA is not tap-to-install software. Public instructions must say
AltStore Classic plus AltServer, explain Developer Mode and refresh limits,
state that no game data is included, and preserve the app container on update.

The maintainer's release authorization does not resolve the upstream
decompilation or translated-code rights boundary. Keep the exact scope in
`RIGHTS_AND_LICENSES.md` and `docs/RIGHTS-STATUS.md` current.
