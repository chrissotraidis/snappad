# PaperPad shell parity

SnapPad's touch shell is maintained as a narrow adaptation of PaperPad commit
`74b6e45830a06c7f274c5ac1ddd7c625bc13a557`, not a visual approximation.
`scripts/audit-paperpad-shell-parity.py` normalizes the approved substitutions
and then requires exact source equality for the following files:

- `ios_main.mm`: identifiers, removal of Paper Mario's private `PSR_AUTOBOOT`
  test seam, Pokémon Snap's bounded input-edge changes, and the audited native
  gyro control and diagnostics/support menu extensions;
- `rom_setup.mm`: identifiers, supported-game wording, exact Pokémon Snap ROM
  size/SHA-1, and private runtime filename;
- `diagnostics.mm`: identifiers plus gyro enablement, sensitivity, and inversion status;
- `touch_tap_latch.h`: class name plus an explanatory provenance comment;
- `Info.plist.in`: product/build-setting identifiers plus the motion usage
  description; and
- `PrivacyInfo.xcprivacy`: byte-for-byte identical.

The shell therefore retains PaperPad's control geometry, gestures, edit mode,
opacity and scale settings, menu behavior, controller ownership, lifecycle
reset behavior, diagnostics export boundary, native document picker, and
privacy declaration. Game-specific control labels and default layout may be
tuned only after Pokémon Snap gameplay is running and the change is added to
this explicit audit rather than silently drifting.

The diagnostics/support extension keeps PaperPad's privacy-reviewed export
flow and places it in a small submenu alongside a direct link to SnapPad's
GitHub issue tracker. It does not upload logs automatically.

The gyro extension remains default-off. Enabling it adds one persisted,
device-class-specific layout control; the in-game button starts or stops
bias-corrected Core Motion sampling and replaces the analog camera axes only
while active. Menus, backgrounding, layout editing, touch disablement, and
physical-controller ownership all pause motion input and clear its axes.

The application-support/Metal path helper is source-derived but excluded from
exact parity because SnapPad adds explicit framework/C-library includes and
expanded guard formatting. Its behavior remains covered by Apple syntax and
bundle builds.
