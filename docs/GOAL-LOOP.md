# SnapPad goal-based loop

Operating loop for maintaining SnapPad as a native Apple-platform product.
`docs/PRD.md` remains the long-term requirements source; this file defines
current execution priority. Reoriented 31 Aug 2026 after the maintainer
accepted the gyro-enabled physical-iPad build and authorized Preview 2.

## Product boundary

SnapPad is the product under test. Pokémon Snap is the compatibility workload.
Desktop acceptance requires proving that SnapPad boots and runs the supported
game, accepts input, renders and plays audio, completes the first-play photo
and scoring loop, persists a real save, survives relaunch, holds cadence, and
packages safely. It does **not** require repeatedly collecting every report
subject before mobile work can begin.

Full-game progression through credits remains a later compatibility and
release gate from the PRD. It is not the active product-development loop and
must not consume repeated manual sweeps when shell, touch, device, or packaging
work can advance.

## Current phase stack

Work the active phase. Reopen an earlier phase only for a demonstrated SnapPad
regression, not for an uncollected Pokémon or an incomplete private save.

### P0 — Reproducible foundation: accepted

- Exact supported ROM, decomp rebuild, ELF/map, AOT generation, overlays, RSP,
  FlashRAM, dependency pins, and private-rights boundary are recorded.
- Host regressions and repository/package safety checks are automated.

### P1 — Native macOS product: accepted

- ARM64 app boots through Metal with generated CPU/audio code.
- Title, menus, camera, photographs, Camera Check, Oak scoring, FlashRAM save,
  clean quit, relaunch, and Continue are proven through stock game paths.
- Keyboard/controller plumbing, 60-minute process stability, and measured
  cadence are proven at the current private-candidate boundary.
- Remaining all-course/credits coverage is tracked under P4, not treated as a
  reason to withhold iPadOS/iOS work.

### P2 — iPadOS/iOS Simulator product: accepted

1. Treat pinned PaperPad as the visual and interaction reference. Port its
   touch controls, spacing, opacity, safe-area behavior, three-dot menu,
   settings, ROM management, diagnostics, lifecycle, and controller ownership
   as identically as Pokémon Snap's required inputs allow.
2. Validate iPad first, then iPhone, with exactly one booted Simulator and one
   SnapPad instance at a time.
3. Prove the core mobile journey across the shared mobile implementation:
   import/recognize ROM → title → touch navigation → Oak's Lab → Beach → hold
   Z and tap A as true simultaneous touch input → photograph stored → pause and
   resume → save/relaunch/Continue. Require the native two-finger shutter on
   iPad, current per-control/layout acceptance on iPhone, and the shared input
   mixer's deterministic Z+A regression. Reserve exact phone grip feel for P3.
4. Capture same-viewport PaperPad/SnapPad comparisons for the title, gameplay
   overlay, and native menu/settings states. Fix visible mismatches before
   broadening the matrix.
5. Record input/screen/presentation cadence during focused gameplay. Treat a
   synchronized Simulator-wide hitch as diagnostic until reproduced on a
   physical device; do not optimize from one isolated bucket.
6. Validate rotation policy, safe areas, background/foreground, ROM replace
   and remove, diagnostics export, and settings persistence in Simulator.
   Reserve physical controller handoff and system-audio interruption for P3.
7. Keep the device build ARM64, AOT-only, ROM-free, path-clean, and auditable.

P2 is accepted at Simulator scope when iPad and iPhone have current screenshots,
iPad has native two-finger shutter evidence, iPhone has current per-control and
layout evidence, the shared multi-touch mixer regression is green, and current
lifecycle, cadence, and audited-bundle evidence exists from the same candidate
revision. Exact phone grip feel and physical-device performance belong to P3;
Simulator evidence must not be presented as either.

### P3 — Physical candidate: accepted for Preview 2 iPad scope

- The signed candidate ran on a physical 12.9-inch iPad Pro with iPadOS 26.6;
  the supported ROM, native Metal/audio paths, and live touch input were
  observed, and Chris accepted the build as stable.
- The native gyro camera path was tuned and accepted hands-on with 190%
  sensitivity, horizontal inversion off, and vertical inversion on. The
  opt-in feature, in-game toggle, settings, and data-preserving update path are
  part of the Preview 2 baseline.
- Dedicated physical-iPhone coverage plus the wider controller, interruption,
  long-soak, and thermal matrix remains post-release compatibility work.
- Preserve the accepted iPad container and its ROM, saves, and preferences on
  every later in-place update.

### P4 — Complete-game compatibility: post-release work

- Finish the fresh-save route through every course, Rainbow Cloud, and credits.
- Cover item/course unlocks, Report, Album, Gallery, later-course interactions,
  repeated transitions, audio breadth, and save persistence.
- Use deterministic stock events when automation is needed. Stop after one
  bounded miss; do not turn report collection into the default work loop.

### P5 — Preview 2 community prerelease: authorized

- Chris explicitly authorized the free v0.1.0 integration-source snapshot and
  unsigned ROM-free IPA on 28 August 2026.
- Chris explicitly authorized the gyro-enabled Preview 2 source snapshot and
  unsigned ROM-free IPA on 31 August 2026.
- Package and repository audits, dependency notices, exact-artifact testing,
  hosted-download verification, and honest unsigned-IPA instructions remain
  mandatory for the authorized release.
- Upstream and translated-code rights remain unresolved; the authorization
  does not extend to paid, commercial, TestFlight, App Store, or official-store
  distribution.

## The operating loop

1. **Orient.** Read `docs/STATUS.md`, the last journal entry, and the active
   phase above. State the user-visible result being advanced.
2. **Check only relevant state.** Confirm the target build, one-instance rule,
   one-Simulator rule, and the specific evidence needed for this step. Do not
   re-audit unrelated hashes, characters, report entries, or source parity.
3. **Compare before changing UI.** Capture the current PaperPad reference and
   SnapPad implementation at the same device/viewport/state.
4. **Change one product behavior.** Prefer the smallest change that improves
   visible fidelity, touch behavior, lifecycle, performance, or packaging.
5. **Test at the correct layer.** Unit-test input semantics; use Simulator for
   native UI and lifecycle; use a physical device for feel, thermal behavior,
   and device performance. Do not substitute one layer for another.
6. **Capture concise evidence.** Keep the accepted screenshot, short runtime
   excerpt, cadence summary, or bundle audit. Reject blank, cropped, stale, or
   wrong-state captures.
7. **Document the result and move on.** Update `STATUS.md` and one journal entry
   when a gate changes. Avoid narrating every probe.

## Hard operating rules

- Never run more than one Simulator or one SnapPad process at a time. Kill and
  shut down before switching device families.
- The original ROM and `ref/paperpad` are read-only. Never commit or upload ROMs,
  saves, generated AOT, photographs, private logs, or extracted game data.
- Preserve unknown local work. Never use destructive cleanup or reset commands.
- Keep production behavior authentic. Test input may automate real controls but
  may not fabricate scores, progression, saves, or game events.
- Two unchanged failures trigger a zoom-out: inspect the product boundary,
  reference implementation, and correct test layer before retrying.
- Do not make performance fixes from mixed menus/gameplay aggregates or one
  isolated Simulator hitch. Measure a focused band and compare input, screen,
  presentation, and audio signals together.
- Do not inspect every character or require textual identity when rendered
  behavior, interaction, and a bounded source-parity audit already prove the
  intended result.
- No public source, package, IPA, screenshot set, tag, or release without the
  explicit P5 authorization.

## Active next action

Publish and independently verify Preview 2, preserve the accepted physical-iPad
container, then continue bounded physical-iPhone and broader compatibility
work. Run Original first; evaluate Wide only afterward as a default-off
enhancement.
