# SnapPad status

Updated: 2026-08-28

## Current gate

**v0.1.0 accepted for a free unsigned community release; broader compatibility work continues.**

The reproducible foundation and current macOS product boundary are accepted.
The exact supported ROM rebuilds byte-for-byte, the CPU and audio RSP outputs
generate under a fail-closed evidence chain, the private ARM64 app passes its
bundle audit, and native runs prove Metal video, generated-RSP audio, input,
the full first-play photograph/scoring loop, FlashRAM save/reload, clean exit,
measured cadence, and a 60-minute soak. Exhaustively collecting report subjects
is no longer the active product-QA loop. Full-course/credits compatibility
remains a later pre-release requirement under P4.

The current mobile candidate has accepted PaperPad-derived iPad and iPhone
layouts, core mobile journeys, native iPad two-finger shutter input, the shared
multi-touch input path, lifecycle behavior, focused cadence, and ROM-free
bundle audits. On 28 August 2026, the signed build ran on a physical 12.9-inch
iPad Pro with iPadOS 26.6, recognized the private supported ROM, initialized the
native Metal and verified audio paths, and recorded live touch input. The
maintainer accepted that build as stable and authorized v0.1.0. Dedicated
physical-iPhone, controller, interruption, sustained-cadence, and thermal
coverage remains post-release compatibility work.

SnapPad now also offers **Wide (Experimental)** as a distinct, default-off
graphics option. Unlike Fill Screen, it uses RT64's expanded projection. A
current iPhone 17 Pro Simulator Beach run widened the renderer-confirmed target
from 1920x1440 to 3131x1440 and visibly exposed additional scene width with a
centered reticle. Authored 2D screens remain 4:3. Photo capture/detection/scoring
correctness in Wide is not accepted, so Original (4:3) remains the default and
the physical handoff must treat Wide as an enhancement check, not baseline.

## Verified state

- SnapPad root began this session at
  `fb7823d78f66be4d97af40bb4cef0ebef4bef1fc` on `main`; the user's pre-existing
  planning-document move into `docs/` remains preserved.
- Pokémon Snap decomp is pinned at
  `11ee0fec2143bdd636ee0e9c714a402fd8c7d9fe`; PaperPad is pinned at
  `74b6e45830a06c7f274c5ac1ddd7c625bc13a557`; dependency push URLs are disabled.
- Rights status records explicit maintainer authorization for the free v0.1.0
  integration-source snapshot and unsigned ROM-free IPA. Upstream and
  translated-code permission remains legally unresolved; no commercial or
  official-store rights claim is made.
- The original supported `.v64` input remains in `ref/`. The ignored normalized
  ROM and exact rebuilt ROM match SHA-1
  `edc7c49cc568c045fe48be0d18011c30f393cbaf`; the ELF, linker map, entrypoint
  `0x80000400`, and artifact hashes are recorded in `generated/evidence/G1.json`.
- N64Recomp/RSPRecomp generation completes. The current model contains 14,919
  CPU functions and generated `aspMain`; G2 evidence records 115 interpreted
  diagnostics and zero unresolved diagnostics.
- Old IDO static functions missing from the linked symbol table are recovered
  conservatively from input-object sizes, linker-map ownership, and direct JAL
  targets. Duplicate private names receive stable address suffixes. The
  generator regression suite covers order disagreement, tight-gap recovery,
  rejection of ordinary references, and direct AI register patches.
- The SP boot probe maps the exact DMEM/IMEM residue checked by Pokémon Snap.
  Controller RAM probes return the documented no-pak result, CP0 WatchLo is a
  bounded no-op, and N64ModernRuntime owns the original VI manager thread.
- Two direct `AI_LEN_REG` reads in `auThreadMain` are derived from the rebuilt
  ELF and redirected to N64ModernRuntime's existing audio-length model. They are
  not mapped to fake MMIO storage.
- The patched runtime prefers a registered verified RSPRecomp audio function
  before Paper Mario's generic audio fallbacks. The accepted native run logged
  `first audio task routed to verified aspMain`, non-zero peaks, bounded queue
  depth, and zero conversion/queue errors.
- `build-macos-app/SnapPad.app` links as ARM64 and passes identity,
  system-dylib-only, path-cleanliness, and no-ROM/source-input audits.
- A one-instance native run rendered the opening and title through Metal. A
  captured title frame is in `logs/design-audit/current/02-later-state.png`.
  Sending Return produced an input edge, left the title, and entered the
  new-game sequence; `03-after-start.png` records the resulting frame.
- The first-play route completed the Beach camera tutorial, reached Camera
  Check both through the pause exit and the natural end-of-course gate, marked
  a Pidgey photo, and returned through Professor Oak's full score flow. The
  empty native offscreen-score readback is recovered only when the authentic
  in-course detector recorded a focused subject at the matching shutter edge;
  the shared score wrapper preserves authentic nonzero results and supplies a
  conservative 1400-point baseline only for that bounded empty-readback case.
- Professor Oak identified the photo as Pidgey, awarded 500 size + 200 pose
  with the centered-photo multiplier for 1400 total, and updated the report to
  1 kind / 1400 points. The explicit save wrote a 131072-byte FlashRAM image
  with SHA-256
  `fbb8b092ba09ccaafe912cba27a82b80a51c4412591c81d1886793a30086dbb8`.
  After a clean exit, both acceptance environment variables were removed; a
  production relaunch loaded Continue and displayed the persisted 1-kind,
  1400-point report.
- Local protected evidence is under `artifacts/2026-08-26/g5-macos/`, including
  the production reload report and natural Beach-to-Camera-Check transition.
- The host CTest suite is 29/29 green. It covers input/accessory policy, touch
  latching, address translation, SP integrity, libultra stubs, generation and
  evidence gates, runtime patch contracts, PaperPad shell/runner derivation,
  packaging, crash capture, breadcrumbs, and decomp recovery tooling.
- A single native macOS process completed a 60-minute stability soak with 14
  natural Beach-to-Oak's-Lab return cycles and no booted Simulator. The final
  30 minutes held 59.957 Hz input/screen cadence while RSS declined from
  128,224 to 127,408 KiB; the full audio trace recorded zero conversion or
  queue errors and no queue depth over 100 ms. SnapPad quit through SDL and the
  protected primary and backup saves remained byte-for-byte unchanged. This
  closes the native duration check, but not photo-review, all-course, or signed
  physical-device coverage.
- The native runner now records opt-in cadence CSVs without changing production
  behavior. A 1,051-second focused run measured mean input and screen-update
  rates of 59.937 Hz and 59.952 Hz. Tunnel gameplay presented at a 29.976 fps
  mean across 958 one-second samples; menus/transitions presented near 60 fps.
  These are current-build measurements, not yet original-hardware equivalence.
- Tunnel's hidden-path route is armed from the game's authentic
  `electrode_WaitForPlayer` condition instead of a wall-clock delay. The
  bundled save had only the apple unlocked, so a test-only environment gate now
  ORs the pester bit into `Icons_Init`'s in-memory return flags without writing
  FlashRAM. Run g47 fired one stock pester, dispatched command 9 to the exact
  behavior-5 guard object `801EB550`, and entered
  `electrode_RevealHiddenPath`. Oak then announced the split path and unlocked
  Volcano.
- Oak's explicit save wrote a 131072-byte FlashRAM image with SHA-256
  `bee0c7732730cde7c979209d69e944d0c9ccad825a59d9f669c9784d15f8a92f`.
  A clean production relaunch with every acceptance variable removed loaded
  Continue and displayed Beach, Tunnel, and Volcano in course selection.
- A test-only, input-only auto-shutter now arms explicitly on F9 after course
  entry and disarms on F8. It holds the stock viewfinder and presses A only
  when the game's own detector reports a Pokémon ID from 1 through 151; it
  never writes scores or progression. A real Beach run produced nine stock
  photographs, passed through Camera Check and Oak's evaluator, and improved
  Butterfree and Pidgey to 3000 points each and Meowth to 40. A Tunnel run
  added Kakuna and improved Zubat. Subsequent accepted Vulpix and Lapras photos
  raised the explicitly saved report to 13 kinds / 29980 points. Matching
  primary and backup 131072-byte FlashRAM images hash to
  `83c74935252dc51a414d04af8ec7d55b306c1e108bb35aa6d111975e940b262f`.
  Volcano also verified that F8 returns to ordinary controls
  and three stock apples clear the Moltres egg; special focus code 600 is now
  ignored so it cannot fill the roll with unusable egg frames.
- Six core Apple shell files pass exact normalized PaperPad parity. The ROM-free
  iPad shell preview previously rendered, exposed accessibility labels, opened
  the native Files picker, handled cancellation, and terminated cleanly on one
  iPad Simulator.
- The production ARM64 iOS Simulator app now builds from the same generated AOT
  core as macOS. The current audited ROM-free bundle is 9.8 MiB, targets iOS
  15+, has no unbundled runtime dependency or private path, and its executable
  SHA-256 is
  `c974d2ca99c1bacd528ab24a14e07bc3665ff8ecbe2035cf14f0c89d935f8c2a`.
- The same production core now builds for the real `iphoneos` SDK as a 9.7 MiB,
  ARM64-only native iPhone/iPad application (`UIDeviceFamily` 1 and 2), with
  iOS 15.0 minimum deployment and no packaged ROM, save, private path, signing
  secret, or non-system dynamic dependency. The telemetry-current executable
  SHA-256 is
  `75182baf791e263ac1865d6b4663a69edb0933d2c959a43b55ffc892deb0e373`.
  The current artifact is intentionally unsigned and has passed
  `scripts/audit-ios-device-bundle.sh`; it is not installable until rebuilt
  with an Apple Development team.
- On one iPad Pro 11-inch (M5) Simulator running iOS 26.5, the production app
  completed fresh ROM validation, title input, photographer-card name entry,
  Oak's introduction, Beach selection, live Metal gameplay, and a real
  Z-held/A-shutter photograph that reduced the roll from 60 to 59. The touch
  overlay remained correctly laid out in landscape and Start, A, B, D-pad, and
  viewfinder/shutter paths produced clean input edges.
- The game-visible Save command wrote matching 131072-byte FlashRAM primary and
  backup images with SHA-256
  `82f45bdbcc866a45adeaad1bc311629d4348d51480d9a910228c8a149462d3d8`.
  A terminated/relaunched production process exposed Continue and restored the
  saved player `A` in Oak's Lab.
- The latest 80 focused iPad gameplay cadence samples averaged 59.893 input
  polls/s, 59.893 screen updates/s, and 29.928 presented frames/s (25.922–31.000
  one-second range) on a 60 Hz simulated display. Evidence is under
  `artifacts/2026-08-27/g9-ipad/`.
- The accepted run used exactly one iPad Simulator and one SnapPad process. The
  process was terminated and the Simulator shut down after evidence capture;
  no second Simulator was booted.
- On exactly one iPhone 17 Pro Simulator running iOS 26.5, the same production
  bundle rendered the PaperPad-derived phone layout in landscape, accepted
  touch Start/A and analog menu input, restored the iPad-created FlashRAM save,
  entered Oak's Lab, selected Beach, and reached live Metal gameplay. The
  cross-device save retained player `A`; no save format conversion was used.
- A released analog flick is now retained for two native polls. The 60 Hz
  native bridge could previously release a one-poll flick between Pokémon
  Snap's menu updates; the two-poll bound moved exactly one menu row in the
  observed phone run without a repeated selection.
- A fresh, save-free iPhone run reached the photographer-card name screen and
  then Oak's Lab using only the touch overlay. It exposed PaperPad's six-poll
  released-button latch as too long for Pokémon Snap: one A tap could enter two
  characters. SnapPad now emits A and Start as one-sample action edges while B,
  Z, directions, and shoulders retain true hold behavior. Re-observation showed
  one A tap adding exactly one character; Start selected End and A confirmed
  the name into Oak's Lab.
- SDL's default iOS Playback audio category kept audio callbacks active after
  Home. SnapPad now requests the Ambient category, pauses and clears the device
  queue on background, discards background samples, and resumes with a fresh
  queue on foreground. The accepted trace records background at 16.358 s and
  foreground at 40.156 s with no intervening audio callback. Before/after live
  Beach captures preserve the same rail/Pidgey state across a ten-second Home
  interval, and rendering resumes without a black frame.
- The latest 80 focused iPhone Beach cadence samples average 59.841 input
  polls/s, 59.841 screen updates/s, and 29.877 presented frames/s
  (25.948–30.969 one-second range). Protected evidence is under
  `artifacts/2026-08-27/g9-iphone/`.
- A separate unattended 45-second Beach window averaged 59.918 input polls/s,
  59.918 screen updates/s, and 29.937 presented fps. One bucket dropped all
  three signals together to 55.888/55.888/27.944 while audio recorded a
  101.385 ms callback gap, then immediately recovered. The trace proves a real
  short whole-process Simulator stall but not a sustained Metal bottleneck or
  physical-device defect. Evidence is under
  `artifacts/2026-08-27/g9-iphone-fresh/`.
- The native iPhone settings sheet is accepted for volume, Auto/2x resolution,
  original/fill aspect, touch-control enablement, and touch opacity, including
  persistence and renderer confirmation. Defaults were restored to 100%, Auto
  (observed 6.00x / 1920x1440), Original (4:3), controls on, and 70% opacity.
- Diagnostics export opens the system share sheet and now correctly reports the
  installed 16 MiB Pokémon Snap ROM as present while excluding ROM/save
  contents. The installed-ROM manager exposes Replace and Remove with the
  rights boundary intact; its dismissal was accepted without modifying data.
- The full installed-ROM replacement cycle is accepted with the verified ROM
  from `ref/`: Files selection, exact validation, visible success confirmation,
  landscape restoration, cold relaunch, and runtime registration all pass. The
  installed/runtime ROM copies retained SHA-256 `a1d5d816…ec1cc`; both saves
  retained SHA-256 `82f45bdb…3d8`. Temporary Files staging copies were moved to
  Trash after acceptance. Remove ROM now targets the actual runtime-copy name.

## Open work and constraints

- P4 still requires the fresh-save progression route through Tunnel,
  Volcano, River, Cave, Valley, Rainbow Cloud, credits, or the required
  course/item unlocks and report/album/gallery behaviors. This is retained as
  a pre-release compatibility gate, not a blocker to current mobile work.
- The verified save now exposes Beach, Tunnel, and Volcano and contains 20 of
  the 22 reported species required by the stock stage-2 River unlock, with
  50,980 report points. The stock rules have been traced directly: River opens
  at 22 reported species, while the Pester Ball additionally requires 72500
  report points at stage 3 or later. River through Rainbow Cloud, credits, later item
  unlocks, and the remaining report/album/gallery paths still require observed
  progression acceptance.
- A new read-only save inspector derives report membership and scores from the
  pinned decomp's `UnkBigBoy` and `D_800AE4E4` layouts. It independently
  confirms the protected save at 20/63 species and 50,980 points without
  launching or modifying SnapPad. The useful early-course missing targets are
  now explicit rather than guessed: Beach includes Chansey, Scyther, and Eevee;
  Tunnel includes Dugtrio, Magneton, Haunter, and Zapdos; Volcano
  includes Charizard, Growlithe, Arcanine, and Moltres. Only two distinct new
  reports are needed for River, and future passes should target one stock
  interaction instead of sweeping already-reported species.
- A bounded Moltres timing run confirmed that an intact egg blocks the Neo-One
  at the Volcano fork as the stock course intends. The delayed apple sequence
  missed the collision window, produced no new report entry, and was rejected
  without a save write. The gameplay band still held 60.013 Hz input/screen
  updates and 29.997 successful presentations/s; one interval exceeded 100 ms.
  The next progression attempt must pivot subjects or trigger from an event
  closer to the egg collision instead of repeating the wall-clock delay.
- One subsequent bounded Tunnel pass tested the stock first-Diglett route. It
  did not focus Diglett, and its low-angle correction missed the block-three
  appearance window; the roll contained only already-reported species and was
  rejected without Oak submission or a save write. The 139-second gameplay
  band averaged 60.029 input polls/s, 60.029 screen updates/s, and 30.011
  successful presentations/s, with no interval over 100 ms. This route is not
  being repeated unchanged.
- One save-informed Beach pass then targeted missing Eevee with the existing
  stock-detector shutter route. It produced seven ordinary photos—Doduo,
  Lapras, Snorlax, Butterfree, Pidgey, Meowth, and Kangaskhan—but the detector
  never exposed Eevee. Every captured subject was already reported, so Camera
  Check was exited without marking, Oak submission, or a save write. The app
  quit through SDL and both protected save hashes remain unchanged. This sweep
  is now exhausted; the next bounded progression attempt should pivot to the
  stock Charizard interaction in Volcano.
- The bounded Charizard pass established its exact stock dependency from the
  pinned decomp: late-course Charmeleon must be knocked into lava before the
  game spawns Charizard. The intact Moltres egg stopped the Neo-One before that
  encounter, so the pass was ended without repeating the already-failed egg
  interaction, Oak submission, or a save write.
- A subsequent bounded Tunnel pass captured Diglett through the ordinary
  shutter and Camera Check path. Oak accepted only that new subject for 3,000
  points, advancing the visible report to 20 kinds / 50,980 points and stating
  that two more pictures remain before the next course. An explicit lab save,
  title return, and clean SDL quit completed normally. The read-only inspector
  independently confirms Diglett in the protected save. The explicit
  progression save produced primary hash `27c2575…2ec`. A later Gallery return
  rewrote save metadata without changing report membership or score; the
  current primary is `136e183…745`, with `27c2575…2ec` rotated to its backup.
- Two differently phased, bounded Tunnel follow-ups targeted Dugtrio and
  Haunter. Neither target entered detector focus; both rolls contained only
  already-reported subjects and were rejected without Oak submission. They
  were ended cleanly and will not be repeated as blind sweeps.
- A bounded Beach interaction then found the rolling pink Chansey disguise and
  used ordinary Pokémon Food, but the shutter was armed after the encounter
  passed. One refined timing pass again missed the brief collision/camera
  overlap and its duplicate Pidgey was rejected. The protected report remains
  exactly 20 species / 50,980 points. A future Chansey attempt must use a
  deterministic item/subject event rather than more UI-timed polling.
- The native runtime now exposes that deterministic event for acceptance runs:
  stock pester and apple impact commands publish the exact target Pokémon ID,
  and the test-only `SNAPPAD_TEST_AUTO_SHUTTER_ARM_ON_ITEM_SUBJECT` input route
  arms the ordinary shutter only after the requested subject is genuinely hit.
  It is inert in production launches and has reset, filtering, and
  single-consumer regression coverage. The rebuilt ARM64 app passed its bundle
  audit. A bounded Chansey evidence run observed real apple impacts on Pidgey
  (subject 16), correctly did not arm for Chansey (subject 113), submitted no
  photos, and left the protected report and both save hashes unchanged. The
  Chansey route is now exhausted rather than awaiting more UI polling.
- The opening capture shows a visible terrain geometry seam. It is recorded as
  a renderer correctness issue and must not be hidden by presentation changes.
- Opening/title audio is active, but scene ambience, Pokémon cries, UI sounds,
  shutter, transitions, pitch, extended underrun behavior, and device output
  remain unverified.
- G8 is accepted at Simulator scope: iPad fresh first-play,
  photo input, save, and reload are accepted, while iPhone fresh title/name,
  Continue, cross-device save restore, Oak's Lab, and live Beach are accepted.
  Native iPad acceptance proves the actual two-finger Z-hold/A-tap shutter; the
  current iPhone pass proves each control, compact layout, and gameplay path;
  both use the same `multipleTouchEnabled` per-`UITouch` bridge. The deterministic
  mixer regression proves held Z and a one-sample A edge coexist for exactly one
  shutter sample. This evidence closes the Simulator product boundary without
  pretending that a mouse-driven Simulator can prove exact phone grip feel.
  That hands-on check remains P3 and Simulator results do not satisfy G11.
- G9 remains open for the full iPad/iPhone matrix. The PaperPad-derived touch
  gameplay and core shell paths are now accepted on iPad; phone layout and
  background/foreground audio handling, native settings, diagnostics export,
  installed-ROM management, and an actual same-ROM replacement/cold-relaunch
  cycle are also accepted. Controller handoff, system audio interruption, and
  the remaining settings/device permutations still need observed acceptance.
- Direct iPad touch-shell visual parity is accepted against the pinned PaperPad
  production AOT build at the same iPad Pro 11-inch (M5) Simulator viewport.
  The combined PaperPad-left/SnapPad-right comparison and individual hashes are
  recorded under `artifacts/2026-08-27/g11-paperpad-visual-parity/` and in
  `design-qa.md`; the six-source shell parity audit also passes.
- A 2026-08-28 reorientation audit rebuilt and re-audited the Release Simulator
  bundle, then captured the current phone gameplay overlay, native settings,
  reset-to-default phone layout, pinned PaperPad phone reference, and current
  iPad landscape layout with one Simulator at a time. No visible layout change
  is warranted: current SnapPad matches the pinned PaperPad source geometry.
  The preserved PaperPad phone binary's top-right utility button predates the
  pinned source's accepted top-center phone slot and is not a regression to
  copy. Evidence and step health are recorded in `design-qa.md` and under
  `artifacts/2026-08-28/p2-iphone-touch-audit/` and
  `p2-ipad-touch-audit/`.
- The same 2026-08-28 candidate rebuilds successfully for `iphoneos` as a
  9.7 MiB unsigned ARM64 app for iPhone and iPad. Its bundle audit confirms the
  iOS 15+ AOT-only, ROM-free, save-free, private-path-free, system-dependency
  boundary. All 29 host tests and repository safety checks pass. Installation
  remains correctly gated on an Apple Development identity, team, and attached
  device.
- Free disk space is approximately 20 GiB. Reuse the existing incremental trees
  and avoid redundant generated builds.
- Physical-device installation is externally gated: `devicectl` currently
  reports no connected device, `security find-identity -p codesigning` reports
  no valid signing identity, and `SNAPPAD_APPLE_TEAM_ID` is unset. This does
  not block iPhone Simulator acceptance or further code-level device work.

## Known-good commands

```sh
scripts/check-prerequisites.sh
scripts/verify-sources.sh
scripts/check-repo-safety.sh
scripts/build-decomp.sh --rom '/absolute/path/to/Pokemon Snap (U) [!].v64'
scripts/generate-game.sh
scripts/build-macos-app.sh
scripts/build-ios-simulator.sh
scripts/build-ios-device.sh --unsigned
cmake -S . -B build-tests -G Ninja
cmake --build build-tests --parallel
ctest --test-dir build-tests --output-on-failure
```

The accepted runtime smoke used the audited executable directly and only one
process at a time:

```sh
build-macos-app/SnapPad.app/Contents/MacOS/SnapPad
```

## Next step

Capture the current iPad and iPhone gameplay overlays at matched PaperPad
viewports is complete with no visible mismatch requiring code changes. Next,
prove the native Z-hold/A-tap shutter on the phone surface and record a focused
gameplay cadence band on one Simulator at a time. Rebuild
with `SNAPPAD_APPLE_TEAM_ID` and install on physical hardware as soon as a
development identity and connected iPad/iPhone exist. Return to P4 full-game
compatibility after the mobile product boundary is accepted.
