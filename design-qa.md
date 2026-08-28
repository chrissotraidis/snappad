# Design QA

Final result: **passed**

## Target and implementation

- Visual target: pinned PaperPad revision
  `74b6e45830a06c7f274c5ac1ddd7c625bc13a557`, running its preserved production
  AOT build on iPad Pro 11-inch (M5) Simulator with iOS 26.5.
- SnapPad implementation: current production AOT Simulator bundle on the same
  Simulator, device orientation, shell window, touch-enabled/inactive state,
  70% default opacity, and Original (4:3) aspect mode.
- PaperPad capture:
  `artifacts/2026-08-27/g11-paperpad-visual-parity/04-paperpad-computer-use-landscape.png`
  (`883fa1d8dff226cb49c8725f11f43c5d6be10a9aa0606fc56c9c70fb4620d4cf`).
- SnapPad capture:
  `artifacts/2026-08-27/g11-paperpad-visual-parity/05-snappad-computer-use-landscape.png`
  (`bccef727aff3541028ed5ce62d27e747342b9f5eae566d0b76bbd64181394290`).
- Combined comparison, PaperPad left and SnapPad right:
  `artifacts/2026-08-27/g11-paperpad-visual-parity/06-paperpad-left-snappad-right-computer-use.png`
  (`ac3bf5bbb0c28ff84f7406fa09136db536a5bbbf0a954c48fd8cc1486de96cf2`).
- Matched Computer Use viewport: 850 x 663 pixels for each capture. Native
  Simulator display: 1668 x 2420 pixels; UIKit landscape bounds: 1210 x 834
  points at 2x scale.

## Comparison result

1. PaperPad was terminated before SnapPad was installed and launched. Exactly
   one iPad Simulator and one game process were active at every point.
2. The reference and implementation were combined into one comparison image
   before judgment. Both overlays were inactive, touch-enabled, and shown at
   the same persisted/default 70% opacity.
3. Analog base and knob, D-pad cluster, A/B/Z, C-button cluster, L/R, Start,
   and the three-dot utility button match in center, scale, spacing, color,
   opacity, stroke, label treatment, and safe-area placement.
4. The centered Original (4:3) viewport and surrounding black shell region
   align. Different game imagery and game-specific system text are not shell
   mismatches.
5. The six-source parity audit independently confirms that PaperPad's UI,
   lifecycle, and privacy implementation differs only through reviewed
   SnapPad substitutions and audited game-specific behavior.

## Findings

No visible PaperPad-to-SnapPad touch-shell mismatch remains in the accepted iPad
landscape state. Phone layout remains separately covered by its source parity,
production screenshots, and functional acceptance; a same-viewport PaperPad
phone comparison can be added when needed, but it is not evidence against this
matched iPad pass.

## 2026-08-28 mobile reorientation audit

Overall verdict: **the current iPad and iPhone touch layouts are visually
healthy; no implementation change is justified by this pass.**

1. **iPhone live gameplay — healthy.** The current Release Simulator bundle
   renders the grip-first landscape layout with separated A, B, Z, C, shoulder,
   Start, analog, D-pad, and utility targets inside the phone safe areas. The
   persisted layout reset returned cleanly to the source-defined defaults.
   Evidence:
   `artifacts/2026-08-28/p2-iphone-touch-audit/11-snappad-reset-landscape.png`.
2. **Pinned PaperPad phone reference — healthy with a stale-binary caveat.** A
   current-run PaperPad capture on the same iPhone Simulator confirms the
   control sizing, color, spacing, and right/left grip model. Its preserved AOT
   binary predates the pinned source's top-center phone utility-button change,
   so its older top-right utility position is not a target regression to copy.
   The audited current PaperPad/SnapPad source pair agrees on top-center.
   Evidence:
   `artifacts/2026-08-28/p2-iphone-touch-audit/07-paperpad-runtime-landscape.png`.
3. **iPhone native settings — healthy.** Volume, resolution, aspect, touch
   enablement, opacity, edit/reset, diagnostics, ROM management, and Done are
   present in a safe-area-bounded native sheet. Reset Touch Layout is functional.
   Evidence:
   `artifacts/2026-08-28/p2-iphone-touch-audit/09-settings-landscape.png`.
4. **iPad landscape — healthy.** The current Release bundle fills the tablet
   landscape surface with the accepted PaperPad-derived tablet geometry; targets
   stay clear of the game center and safe-area edges. Evidence:
   `artifacts/2026-08-28/p2-ipad-touch-audit/04-landscape-upright.png`.

Accessibility limit: the persistent utility button and native settings expose
useful accessibility labels, but the custom-drawn gameplay controls are not
individually represented in the captured accessibility tree. Screenshots do not
prove VoiceOver operability, physical reach, or simultaneous two-finger touch.
Those remain interaction/device checks rather than visual mismatches.
