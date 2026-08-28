# SnapPad engineering journal

Append-only. Acceptance claims distinguish source inspection, compilation, launch, Simulator observation, and physical-device observation.

## 2026-08-26 — G0 environment and source state

- **Hypothesis:** the workspace can be made reproducible and publication-safe before any ROM-derived build begins.
- **State checked:** root revision and dirty state, booted Simulators, SnapPad processes, available tools, disk capacity, current reference revisions, source licenses, and scoped ROM inputs.
- **Actions:** read `docs/PRD.md` before `docs/GOAL-LOOP.md`; pinned PaperPad to `74b6e45830a06c7f274c5ac1ddd7c625bc13a557`; cloned the Pokémon Snap decomp at `11ee0fec2143bdd636ee0e9c714a402fd8c7d9fe`; disabled push for both; installed `uv`; selected a separate integration-repository topology.
- **Result:** exact source references are locally available and no Simulator/game instance is active. The pinned decomp has no general root license. No supported ROM exists in the scoped SnapPad input locations.
- **Evidence:** Git revisions and environment output captured in the active task transcript; durable state is recorded in `dependencies.lock.json`, `docs/RIGHTS-STATUS.md`, and `docs/STATUS.md`.
- **Interpretation:** continue G0. G1 will require a user-provided ROM path and must not search broadly through private user files.
- **Next:** finish executable verification/safety scripts, validate them, then scaffold the ROM normalization and exact decomp build path.

## 2026-08-26 — G0 completed; G1 prepared

- **Hypothesis:** the complete ROM-free G0 boundary and a fail-closed G1 entry point can be verified without accessing a user ROM.
- **Step:** created the SnapPad dependency lock, rights/status/inventory documents, PaperPad-style README, ignored-data boundary, prerequisite/source/safety scripts, byte-order normalizer, and exact decomp build driver. Cloned all locked top-level inputs and disabled their push URLs.
- **Commands:** `scripts/check-prerequisites.sh`; `scripts/verify-sources.sh`; `scripts/check-repo-safety.sh`; `bash -n scripts/*.sh scripts/lib/*.sh`; `git diff --check`.
- **Result:** all listed checks pass. Host reports Apple Silicon, Xcode 26.6, Metal toolchain, `uv 0.12.6`, and approximately 31 GiB free. No Simulator or SnapPad instance was launched.
- **Evidence:** durable scripts and documents in the SnapPad tree; exact revisions in `dependencies.lock.json`.
- **Interpretation:** G0 is met. G1 is the lowest unmet goal and is prepared but cannot execute without an explicit supported ROM input.
- **Next:** read the remainder of the pinned PaperPad implementation guidance, then extract game-neutral shell/runtime mechanisms while leaving G1 visibly unmet until the ROM is supplied.

## 2026-08-26 — ROM-free Apple shell extraction and iPad Simulator smoke

- **Hypothesis:** PaperPad's game-neutral ROM import, diagnostics, settings, touch overlay, touch latch, and controller ownership mechanisms can be ported closely enough to build and exercise without importing Paper Mario-specific game code.
- **Step:** ported the pinned PaperPad Apple shell with SnapPad identifiers; changed the ROM gate to the exact 16 MiB Pokémon Snap US SHA-1; removed the Paper Mario-specific autoboot environment carryover; added a ROM-free shell-preview target, controller/touch-latch tests, Apple syntax check, and bundle audit.
- **Commands:** host CMake/Ninja build and CTest; `scripts/check-apple-shell-syntax.sh`; `scripts/build-ios-shell-preview.sh`; one iPad Pro 11-inch (M5), iOS 26.5 Simulator install/launch; native Files picker interaction; `xcrun simctl io ... screenshot`; terminate and shutdown.
- **Result:** two host tests pass. All three Objective-C++ shell sources pass arm64 Simulator syntax checking (one inherited UIKit deprecation warning). The ROM-free arm64 app builds and launches. The first-run screen rendered in landscape with correct SnapPad/Pokémon Snap wording and accessibility identifiers; Choose ROM opened the native picker; cancellation returned `No ROM selected`; the app terminated without a SnapPad crash. Exactly one Simulator was booted and it was shut down afterward.
- **Evidence:** ignored `docs/artifacts/2026-08-26/snappad-ipad-shell-first-run.png`, SHA-256 `dec16cac14f4cd0df60df619c57d2cc05607d9b9d8120b014ca582f26f42f8c6`; task transcript contains the landscape UI/picker inspection.
- **Interpretation:** the reusable Apple shell is now real buildable code, but its gameplay overlay has not run over the game and G1/G8/G9 remain unmet. The Simulator screenshot is portrait-framebuffer evidence, matching PaperPad's documented `simctl` quirk.
- **Next:** audit and stage the applicable PaperPad runtime/RT64 patch set, generate Pokémon Snap-specific configuration/inventories from source where possible, and execute G1 immediately when the supported ROM path is available.

## 2026-08-26 — game-neutral PaperPad patch stack

- **Hypothesis:** the exact PaperPad Apple/Metal/AOT mechanisms can apply to the pinned ReCut source without importing game-specific Paper Mario behavior.
- **Step:** copied and classified 21 maintained patches; excluded all audio, cadence, FlashRAM, and gameplay-specific changes; added an idempotent exact-pin patch driver.
- **Result:** the stack applies cleanly and an unchanged second run reports every patch already applied. One overlap was found: PaperPad's Fill Screen patch already contains the `rt64_present_queue.cpp` portion of its worker-lifetime patch. SnapPad removed only that duplicated file section from the later patch and documented the rebase; the remaining worker-lifetime changes apply cleanly. ReCut `git diff --check` and SnapPad repository safety pass.
- **Interpretation:** Apple runtime/renderer source is ready for host-tool and later native builds. No excluded game-specific patch has been treated as applicable to Pokémon Snap.
- **Next:** build N64Recomp/RSPRecomp host tools, then prepare configuration generation to consume only the verified G1 ELF/map.

## 2026-08-26 — pinned recompilation host tools

- **Hypothesis:** the PaperPad-pinned, game-neutral-patched N64Recomp tree can produce native host tools before ROM-derived generation begins.
- **Command:** `SNAPPAD_BUILD_JOBS=6 scripts/build-host-tools.sh`.
- **Result:** Release `N64Recomp` and `RSPRecomp` compiled successfully with AppleClang. `N64Recomp` SHA-256 is `d89a4b44e71987e0318042b82852cd9fed1c15b06750faa40d4038f27c9090b1`; `RSPRecomp` SHA-256 is `6fefec45ca19a184257ddf26148c4965253ccd812fcd1ff765418842120c3fc8`.
- **Interpretation:** host-tool compilation is proven, but no Pokémon Snap AOT/RSP generation claim exists without the verified G1 ELF/ROM and game-specific configuration.
- **Next:** execute G1 with the supported ROM, derive entry point/section identities from its ELF/map, and generate the minimal Pokémon Snap config with every warning recorded.

## 2026-08-26 — reproducible decomp tools and provisional executable inventory

- **Hypothesis:** G1's remaining toolchain and G2's source-level discovery can
  advance without guessing addresses or accessing a user ROM.
- **Step:** built GNU MIPS binutils 2.46.1 from its SHA-512-pinned archive;
  installed the decomp's `uv` lock, IDO 5.3/7.1, and asm-processor 1.0.1;
  recorded and verified their Apple Silicon executable hashes; added a
  fail-closed ELF-derived N64Recomp config/generation path; generated a
  provisional segment/overlay/RSP inventory from the exact decomp source.
- **Commands:** `SNAPPAD_BUILD_JOBS=6 scripts/build-mips-binutils.sh`;
  `uv sync --frozen`; `uv run configure.py --setup`;
  `scripts/verify-decomp-toolchain.sh`;
  `scripts/inventory-source-layout.sh`.
- **Result:** toolchain verification passes and the Pokémon Snap checkout is
  clean. The inventory contains 54 code segments, 30 declared overlay table
  entries, and four source-declared RSP blobs. The AOT config generator's
  negative test rejects the absent `build/pokemonsnap.elf` without output.
- **Interpretation:** ROM-free setup is ready. G1 remains unmet because only the
  supported ROM can prove the matching rebuild, ELF/map, and entrypoint. The
  overlay inventory reveals extensive shared VRAM windows, so final generation
  must preserve ROM-to-VRAM identities across scene transitions.
- **Next:** when the supported ROM is supplied, run `scripts/build-decomp.sh`,
  record artifact hashes/entrypoint, then run `scripts/generate-game.sh` and
  interpret every N64Recomp warning before any native link claim.

## 2026-08-26 — native SDL2 and RT64 shader prerequisites

- **Hypothesis:** PaperPad's game-neutral native dependency lane can be
  reproduced now without generated Pokémon Snap code.
- **Command:** `SNAPPAD_BUILD_JOBS=6 scripts/build-rt64-host-tools.sh` (which
  applies the reviewed patch stack idempotently and builds pinned SDL2 first).
- **Result:** SDL2 2.32.10 produced `libSDL2.a` (SHA-256
  `0e4cc7bca30b4f9bf617a7bb94128fc25591d1c1527d17fd4879dbf994fcf0dc`).
  RT64 produced `file_to_c` (SHA-256
  `e38abf3ad775aeb8084d82ba5577e71817fec58df130e7e20b1b908c1a7c0db4`)
  and `spirv_cross_msl` (SHA-256
  `99148efce8c167efea0e338ebfe9743b7dfa6cc53de3f5ec8d94ab42e55bd94f`).
- **Interpretation:** native Apple shader-generation prerequisites are proven.
  This is not a G3 game compilation/link claim; that still requires verified
  G1 artifacts and interpreted G2 generation.
- **Next:** keep the cached tools, avoid duplicate build trees, and execute the
  exact rebuild/AOT path when the supported ROM is supplied.

## 2026-08-26 — ROM-free regression sweep

- **Commands:** prerequisite/source/safety checks; decomp-tool verification;
  iOS shell bundle audit; host CMake build and CTest; `generate-game.sh`
  negative gate; reference checkout status; both repository diff checks; and
  booted-Simulator inspection.
- **Result:** all positive checks pass, including 3/3 host tests. AOT generation
  exits at the intentionally absent rebuilt ELF and writes no output. Pokémon
  Snap, SDL2, and PaperPad reference checkouts are clean; ReCut's reviewed patch
  diff is whitespace-clean; no Simulator is booted.
- **Interpretation:** the current ROM-free baseline is internally consistent.
  G1 remains the lowest unmet gate and cannot be truthfully advanced without
  an explicit supported user ROM input.

## 2026-08-26 — deterministic G1 handoff and save/accessory contract

- **Hypothesis:** all runtime identities and Pokémon Snap device policy that do
  not require gameplay can be made fail-closed before a ROM is supplied.
- **Step:** added exact G1 evidence recording, ROM-range RSP finalization, a
  pinned-xxHash XXH3 helper, generated native game metadata, overlay
  registration compilation, FlashRAM full-chip boundary correction, and
  executable save/accessory/game-registration policies.
- **Result:** runtime registration is constrained to 128 KiB FlashRAM; port 1
  exposes a standard controller with no pak; ports 2–4 are absent. The XXH3
  helper matches published empty and `abc` vectors. Full-chip erase now accepts
  the valid `[0, 0x20000)` range without importing Paper Mario page wrapping.
  Every artifact-dependent script rejects the current missing-ROM state.
- **Evidence:** `docs/SAVE-AND-ACCESSORIES.md`,
  `port/runtime/game_registration.cpp`,
  `port/runtime/accessory_policy.cpp`, and host CTest.
- **Interpretation:** these are compiled policy contracts, not persistence or
  accessory acceptance. The runtime matrix begins only after a runnable build.
- **Next:** continue the G2 source audit while G1 waits for the supported ROM.

## 2026-08-26 — runtime-loaded MIPS path isolated

- **Hypothesis:** VPK0 regions are data unless source evidence proves they can
  execute.
- **Step:** audited all VPK0 loads and instruction-cache invalidations in the
  pinned game source and extended the machine-readable source inventory.
- **Result:** menu and intro VPK0 payloads are referenced as sprite/texture/
  animation data. `unk_segment_AA18E0_vpk0` is different: the game decompresses
  it to `0x80200000` and calls it during an SP-integrity/illegal-copy check.
  SnapPad now injects a single entry hook into `func_80364360_504770`; it calls
  the original recompiled `setPlayerFlag(PFID_ILLEGAL_COPY, true)` if either
  ELF-derived SP integrity byte is false. Healthy, IMEM-failed, DMEM-failed,
  and both-failed cases pass in the host regression.
- **Evidence:** `docs/OVERLAYS.md`, schema 2 of ignored
  `generated/inventory/source-layout.json`,
  `port/runtime/snappad_game_hooks.cpp`, and 8/8 host CTest.
- **Interpretation:** this removes an otherwise guaranteed AOT lookup failure
  without turning the check into a no-op. G2 remains unmet until the exact
  payload is extracted/disassembled and compared and the route runs in-game.
- **Next:** execute G1 when the supported ROM is provided, then generate AOT,
  interpret every warning, validate the integrity payload, and compile the
  first native macOS core.

## 2026-08-26 — ROM-free baseline revalidated

- **Commands:** prerequisite/source/repository/decomp-tool checks; idempotent
  patch application twice; ReCut/root whitespace checks; shell syntax/build/
  bundle audit; host CMake/CTest; negative G1/AOT gates; reference cleanliness;
  process and booted-Simulator inspection.
- **Result:** all positive checks pass, including 8/8 host tests and the arm64
  iOS shell bundle audit. The only compiler diagnostic is the inherited UIKit
  `UIButton.contentEdgeInsets` deprecation. G1 evidence rejects the missing
  normalized ROM, AOT generation rejects the missing rebuilt ELF, and neither
  writes a config/metadata artifact. Pokémon Snap, PaperPad, and SDL2 remain
  clean; the reviewed ReCut diff is whitespace-clean. No Simulator is booted
  and no SnapPad instance is running.
- **Interpretation:** the repository remains internally consistent after the
  save/accessory and dynamic-code work. G1 is still the lowest unmet goal.
- **Next:** provide the supported US ROM explicitly to
  `scripts/build-decomp.sh --rom /absolute/path/to/rom`; do not search outside
  the scoped input locations.

## 2026-08-26 — RSP generation and generated-core rung staged

- **Hypothesis:** a valid G1 output should flow into audio-RSP generation and a
  complete generated-source compilation without copied Paper Mario constants
  or silently ignored diagnostics.
- **Step:** added evidence-derived `aspMain` configuration, IPL3 boot-address
  validation, DMEM dispatch-target derivation, exact diagnostic auditing, an
  empty-by-default interpreted-warning allowlist, and a generated CPU/RSP/glue
  static-archive target.
- **Result:** host tests cover address normalization, out-of-range rejection,
  boot-address instruction validation, unsupported-instruction exclusion,
  clean/unknown/interpreted/ambiguous diagnostics, and absent-AOT configure
  rejection. All fail closed without the ROM. No audio behavior is claimed.
- **Evidence:** `scripts/generate-rsp-config.py`,
  `scripts/audit-generation-logs.py`, `scripts/compile-generated-core.sh`,
  `config/generation-warning-allowlist.json`, and host CTest.
- **Interpretation:** post-ROM generation now has a reproducible path to the
  first compile rung. RSP task correctness remains a runtime gate.
- **Next:** execute G1 with the supported ROM, run both recompilers, interpret
  their actual output, and compile the generated core.

## 2026-08-26 — PaperPad shell fidelity made executable

- **Hypothesis:** "PaperPad-derived" should be testable as exact source parity,
  not inferred from similar screenshots.
- **Step:** normalized audited product/game substitutions against the pinned
  PaperPad commit and compared six UI/lifecycle/privacy sources exactly.
- **Result:** parity passes. `ios_main.mm` differs only by identifiers and the
  deliberate removal of Paper Mario's `PSR_AUTOBOOT`; ROM setup differs only
  by Pokémon Snap's exact size/hash/writing; diagnostics is identifier-only;
  the touch latch changes only its class/provenance comment; Info.plist changes
  product variables; the privacy manifest is byte-identical.
- **Evidence:** `scripts/audit-paperpad-shell-parity.py` and
  `docs/PAPERPAD-PARITY.md`. Host CTest is 12/12 green.
- **Interpretation:** the user's UI-fidelity requirement is now protected
  against accidental drift. Gameplay acceptance still requires G1–G8.
- **Next:** keep parity green while wiring the same shell to the generated core.

## 2026-08-26 — dynamic-code review artifact made deterministic

- **Hypothesis:** replacing the one runtime MIPS call is only auditable if the
  exact decompressed payload and its instruction stream are durable evidence.
- **Step:** added a post-G1 audit before N64Recomp/RSPRecomp generation. It
  derives the `0xAAA610..0xAAA65B` range from the pinned segment map, verifies
  the ROM against G1, uses the decomp's VPK0 codec, and requires GNU MIPS
  objdump to decode every four-byte word at the real `0x80200000` load address.
- **Result:** the source parser is checked against the actual nested YAML shape;
  missing/implicit bounds and partial disassembly fail. Evidence records hashes,
  sizes, instruction count, and mnemonic inventory while retaining
  `equivalenceReview: pending` and `gateComplete: false`. The full host suite is
  13/13 green. The arm64 iOS shell syntax, build, and bundle audit also pass;
  the inherited `UIButton.contentEdgeInsets` deprecation remains the only
  compiler diagnostic. No Simulator was booted.
- **Evidence:** `scripts/audit-dynamic-code.py`,
  `tests/audit_dynamic_code_test.py`, `docs/OVERLAYS.md`, and host CTest.
- **Interpretation:** post-ROM inspection can no longer skip the opaque payload,
  but equivalence and runtime behavior remain unclaimed until G1 supplies it.
- **Next:** run G1 with the supported ROM, let generation emit the exact payload
  evidence, review the native hook against it, and compile the generated core.

## 2026-08-26 — native Apple runtime stack compiled without ROM bytes

- **Hypothesis:** the large SDL2/N64ModernRuntime/RT64/Metal dependency graph
  can be validated independently of Pokémon Snap generation.
- **Step:** added a native macOS CMake profile and resumable build script using
  the pinned SDL2 and zstd sources plus the reviewed ReCut patch stack. The
  first configure exposed the missing external-zstd variable; the first shader
  build exposed DXC's archive-lost executable bit. Both prerequisites are now
  explicit and fail closed, including source-clone preparation for fresh runs.
- **Result:** `librecomp`, `ultramodern`, all RT64 Metal shader intermediates,
  and `rt64.a` compiled successfully. The three delivered archives are
  arm64-only, and the build command database proves librecomp used
  `N64MODERN_NO_DYNAMIC_CODE=1`. The isolated tree occupies 51 MiB.
- **Evidence:** `SNAPPAD_BUILD_JOBS=6 scripts/build-macos-runtime-stack.sh` and
  `build-macos-runtime/{runtime/librecomp, runtime/ultramodern, rt64}`.
- **Interpretation:** native dependency compilation is no longer behind G1.
  The game core, runner link, rendering behavior, audio, and timing remain
  unclaimed until exact generated sources are available and exercised.
- **Next:** after G1, compile the generated core against this validated stack,
  then add the game-neutral runner callbacks without importing Paper Mario
  cadence, diagnostics, accessory, or renderer assumptions.

## 2026-08-26 — SnapPad native runner reaches the real linker

- **Hypothesis:** PaperPad's reusable host plumbing can be made link-complete
  before G1 without treating fixture game behavior as executable evidence.
- **Step:** derived the SDL/audio/input/window/ROM/runtime callback runner from
  the exact PaperPad source, removed its scene/frame/texture/game-identity
  behavior, substituted Pokémon Snap's no-pak policy and generated identity,
  and added a conservative RT64 Metal context. A link-only target supplied only
  the unavailable entrypoint and audio-RSP symbols as explicitly scoped test
  fixtures, then linked the real native dependency graph.
- **Result:** the first link exposed only `recomp_translate_address`. The new
  RDRAM/TLB bridge passes cached, uncached, sign-extension, map, unmap, and
  masked-index tests; the arm64 link probe then succeeded. The production
  `SnapPad.app` target is staged and correctly rejects the absent metadata.
  Exact PaperPad runner derivation and renderer carryover policy are tested.
- **Evidence:** `docs/RUNNER.md`, `port/runtime/snappad_runner.cpp`,
  `port/runtime/snappad_rt64_context.cpp`,
  `port/runtime/address_translation.cpp`, and
  `build-macos-runtime/snappad_native_link_probe` (link-only; never run).
- **Interpretation:** all known ROM-free macOS host ABI/link work is now real.
  G3 remains unmet because no ROM-derived functions exist and the probe is not
  a game executable.
- **Next:** complete G1, generate CPU/RSP output, review the dynamic payload,
  compile the generated core, link the production bundle, then boot one macOS
  instance with runtime/overlay/RSP breadcrumbs.

## 2026-08-26 — generated output identity bound to app builds

- **Hypothesis:** existence checks alone can accidentally accept stale ignored
  AOT output after a ROM, ELF, config, or hook changes.
- **Step:** upgraded generation evidence to schema 2 with deterministic hashes
  for G1, both configs, generated game metadata, dynamic-code evidence, every
  CPU source, and the audio RSP. Added a verifier to both generated-core and
  native-app build entry points.
- **Result:** manifest hashing is order-independent and content-sensitive in
  regression tests. App build still stops at the first absent verified input;
  a future stale or modified generated tree will stop at identity verification.
- **Evidence:** `scripts/audit-generation-logs.py`,
  `scripts/verify-generated-evidence.py`, and host CTest.
- **Interpretation:** G2/G3 artifacts now form one evidence chain instead of a
  collection of independently existing files.
- **Next:** populate the chain only from the supported exact ROM.

## 2026-08-26 — native artifacts made path-clean and package-auditable

- **Hypothesis:** a successful native link can still be non-reproducible or
  accidentally depend on the developer checkout.
- **Step:** added compiler prefix mapping to SnapPad and its separately built
  SDL2, rebuilt the full native graph, and made the runtime-stack entry point
  reject non-arm64 output, non-system dylibs, or the absolute checkout path.
  Added the corresponding production bundle audit, including bundle identity
  and rejection of packaged ROM, ELF, map, header, or generated-source inputs.
- **Result:** all 651 rebuilt runtime/link steps completed. The link-only arm64
  probe has system-only dynamic dependencies and contains no checkout path.
  The production audit is wired after the real `SnapPad.app` link and remains
  intentionally unexecuted until verified G1/G2 output exists.
- **Evidence:** `scripts/audit-native-link-probe.sh`,
  `scripts/audit-macos-app.sh`, and `scripts/build-macos-runtime-stack.sh`.
- **Interpretation:** the ROM-free native boundary is now link- and
  package-hardened; this does not advance the gameplay gates.
- **Next:** rerun the complete ROM-free validation ladder, then continue
  tightening the exact post-G1 handoff while awaiting the supported ROM.

## 2026-08-26 — production Simulator graph and first-boot diagnostics staged

- **Hypothesis:** the validated Apple shell and native AOT runner can be joined
  for Simulator without relaxing the exact generated-output gate.
- **Step:** extended the shared Apple runtime graph with PaperPad's iOS
  cross-compile profile, host RT64 shader tools, pinned in-tree SDL2, UIKit
  sources, and an arm64 Simulator bundle audit. Added PaperPad-derived crash
  capture plus bounded core/overlay/RSP/render/dynamic-code breadcrumbs.
- **Result:** the production Simulator command rejects the first missing G1
  metadata file before configuration. Its package audit passes against the
  current arm64 shell bundle, and the real runner/RT64 context pass an arm64
  Simulator cross-syntax check. The macOS runtime probe still links and passes
  its architecture/dependency/path audit. PaperPad's applicable README first-
  launch, controls, diagnostics, FAQ, and credits structure is also adapted and
  regression-protected; the host suite is 21/21 green.
- **Evidence:** `scripts/build-ios-simulator.sh`,
  `scripts/audit-ios-simulator-bundle.sh`, `scripts/capture-crashes.sh`, and
  `tests/runtime_breadcrumb_contract_test.py`.
- **Interpretation:** both Apple production targets now consume the same
  evidence-gated AOT core. No production Simulator core or gameplay claim is
  made until G1/G2 output exists and the real target builds and runs.
- **Next:** supply the exact supported ROM, execute G1, generate and inspect
  CPU/RSP output, then build and boot the macOS app before Simulator gameplay.

## 2026-08-26 — exact rebuild, AOT generation, and native G4 title boot

- **Goal:** complete G1–G4 and identify the first honest G5 blocker.
- **Hypothesis:** the supported ROM in `ref/` can close the exact-rebuild chain;
  remaining native failures will be bounded ABI or old-IDO metadata gaps rather
  than a need for an emulator or containerized toolchain.
- **Step:** normalized the user ROM without modifying the original; rebuilt the
  decomp; recovered old IDO static functions from object sizes, linker ranges,
  and direct linked call targets; generated CPU and audio RSP sources; linked
  and audited the native app; then iterated one process at a time through SP
  boot-memory mapping, three bounded libultra stubs, and two direct AI length
  reads redirected to N64ModernRuntime's existing model.
- **Result:** the rebuilt ROM matches SHA-1
  `edc7c49cc568c045fe48be0d18011c30f393cbaf`; N64Recomp reports 14,918
  functions; generation evidence reports 115 interpreted and zero unresolved
  diagnostics; `SnapPad.app` is ARM64, system-dylib-only, path-clean, and
  contains no ROM/source inputs. A native launch rendered the opening and title
  through Metal, routed audio to verified `aspMain`, produced non-zero samples
  with zero conversion/queue errors, accepted Start, and entered the new-game
  sequence. The process was terminated before another launch. No Simulator was
  booted.
- **Evidence:** `generated/evidence/G1.json`,
  `generated/evidence/G2-generation.json`, `logs/n64recomp-generate.log`,
  `logs/rsprecomp-audio-generate.log`,
  `logs/design-audit/current/01-native-runtime.png`,
  `logs/design-audit/current/02-later-state.png`, and
  `logs/design-audit/current/03-after-start.png` (all protected/local where
  applicable). Host CTest is 26/26 green.
- **Interpretation:** G1, G2, G3, and G4 are met. A title screen is not a
  playable-port claim; G5 is now the lowest unmet goal. The visible opening
  frame also exposed a terrain seam that remains a renderer correctness issue.
- **Next:** run one disposable-save macOS instance through new game, Oak's Lab,
  Beach photographs, review/scoring, FlashRAM write, clean exit, and relaunch;
  stop at the first causal gameplay, overlay, save, audio, or renderer defect.

## 2026-08-26 — macOS first-play loop and FlashRAM reload completed

- **Goal:** complete G5 without treating a title boot, process launch, or
  pause-menu course exit as a finished first-play proof.
- **Hypothesis:** Camera Check's offscreen rerender is valid on N64 but its
  native Metal readback is empty; the authentic in-course detector result can
  recover identity conservatively without replacing nonzero game scores.
- **Step:** correlated A+Z shutter edges with the detector's rebuilt-ELF-derived
  focus globals; reset the correlation queue at every detector/course start;
  moved the empty-readback recovery from one Camera Check caller into the
  shared score wrapper; regenerated all AOT sources; rebuilt and audited the
  ARM64 app; then ran exactly one app through Beach, Pidgey selection, Oak's
  score breakdown, report update, explicit save, clean exit, production
  relaunch, and a separate uninterrupted natural Beach endpoint.
- **Result:** Oak identifies Pidgey (internal ID 16), awards 500 size + 200 pose
  and the centered-photo multiplier for 1400 total, and updates the report to
  1 kind / 1400 points. The natural course reaches Camera Check without using
  Quit Course. The 131072-byte FlashRAM save hashes to
  `fbb8b092ba09ccaafe912cba27a82b80a51c4412591c81d1886793a30086dbb8`.
  After removing `SNAPPAD_TEST_Z_HOLD_POLLS` and
  `SNAPPAD_PHOTO_SCORE_TRACE_PATH`, a clean production relaunch loads Continue
  and displays the persisted report. No Simulator was booted.
- **Evidence:** protected local screenshots in
  `artifacts/2026-08-26/g5-macos/`, generated hook sites in
  `generated/aot/snappad-us.toml`, the FlashRAM hash above, and the 26/26 host
  regression plus native bundle, PaperPad parity/derivation, and repository
  safety audits.
- **Interpretation:** G5 is met. The fallback is deliberately fail-closed: it
  leaves authentic nonzero scores untouched and recovers only a shutter-tagged
  subject after an empty native readback. G6 is now the lowest unmet goal.
- **Next:** score at least five additional Beach species to unlock Tunnel, then
  complete the macOS course/unlock sequence through Rainbow Cloud and credits.

## 2026-08-27 — cadence measured and Tunnel trigger made game-state-driven

- **Goal:** continue G6 and establish the first measured G7 timing evidence
  without treating visual screenshots as an input clock.
- **Hypothesis:** the Tunnel Electrode attempts drift because route durations
  count emulator input polls while validation observes presented frames; using
  the game's own hidden-path readiness condition will remove that ambiguity.
- **Step:** added opt-in CSV telemetry for controller polls, emulator screen
  updates, RT64-confirmed presentations, display refresh, focus, and minimize
  state. Measured a 1,051-second native run, inspected the verified decomp's
  behavior-5 Electrode logic, and generated audited hooks at
  `electrode_WaitForPlayer` block 5 / part 0.35 and
  `electrode_RevealHiddenPath`. Added a progress-triggered deterministic route,
  regenerated the entire AOT/evidence chain, rebuilt the native app, and added
  host regression coverage for the single-consumer trigger.
- **Result:** input and screen updates hold near 60 Hz while focused Tunnel
  gameplay presents at a 29.976 fps mean; menu/transition samples present near
  60 fps. Generation still reports 115 interpreted diagnostics and zero
  unresolved diagnostics, and host CTest is 26/26 green. Volcano is not yet
  unlocked: the new trigger run is waiting safely because the Mac is locked.
- **Evidence:** `artifacts/2026-08-27/g7-frame-cadence.csv`, `docs/PERF.md`,
  `generated/aot/snappad-us.toml`,
  `generated/evidence/G2-generation.json`, and the 26/26 host test run.
- **Interpretation:** route time is now measured correctly: gameplay uses about
  60 input polls for 30 presented frames each second. The remaining test is an
  aiming/interaction problem at an exact game-state boundary, not an unknown
  wall-clock or focus-pause problem.
- **Next:** unlock the Mac, drive the waiting single native instance through
  Continue and Tunnel, require both readiness and reveal trace records, then
  verify Volcano appears before advancing G6.

## 2026-08-27 — Tunnel hidden path revealed and Volcano persisted

- **Goal:** remove the first G6 progression blocker with causal native evidence,
  one process at a time and without booting a Simulator.
- **Hypothesis:** the route was failing before ballistics: the saved profile had
  only the apple icon, so B presses could not create a pester ball. Once the
  stock item was available, trajectory telemetry could replace blind reticle
  tuning.
- **Step:** added an environment-gated, in-memory pester flag at the verified
  `Icons_Init` post-`getProgressFlags` instruction; it never writes the unlock
  to FlashRAM. Hooked stock item movement, exact guard identity, impact
  commands, and `electrode_RevealHiddenPath`. A clean route acquired the exact
  behavior-5 Electrode, applied a staged upward arc then left lead, and released
  one pester. After Oak announced the split path, used the game's explicit Save
  command and relaunched with all acceptance variables removed.
- **Result:** g47 dispatched command 9 to guard `801EB550` and immediately
  entered `electrode_RevealHiddenPath`. The explicit 131072-byte FlashRAM save
  hashes to
  `bee0c7732730cde7c979209d69e944d0c9ccad825a59d9f669c9784d15f8a92f`.
  A clean production Continue displays Beach, Tunnel, and Volcano. Host CTest
  remains 26/26 green; native bundle, PaperPad runner derivation, and shell
  parity audits pass. No Simulator was booted and no process was left running.
- **Evidence:** `artifacts/2026-08-27/g47-gameplay.log`,
  `artifacts/2026-08-27/g46-frame-cadence.csv`, generated hook sites in
  `generated/aot/snappad-us.toml`, and the FlashRAM hash above.
- **Interpretation:** the blocker was missing item capability plus a bounded
  moving-target lead, not rendering, timing, or ROM input. G6 advances to
  Volcano; the temporary item capability exists only in explicit acceptance
  runs and production behavior/save semantics remain authentic.
- **Next:** complete Volcano, explicitly save, and require River to survive a
  clean production reload before continuing the later-course chain.

## 2026-08-27 — authentic photo loop automated and report advanced

- **Goal:** make the long G6 species/report path driveable through ordinary
  camera input while preserving the game's selection, scoring, and save logic.
- **Hypothesis:** the game already exposes the focused subject at the shutter
  boundary, so a test-only input harness can wait for that signal and press the
  real A button without fabricating photos, scores, or progress.
- **Step:** exposed the existing focused-subject observer to the native runner;
  added an F9-armed/F8-disarmed auto-shutter that holds Z and pulses A only for
  Pokémon IDs 1–151; mirrored it in the PaperPad runner derivation audit. Ran
  Beach and Tunnel to natural Camera Check, manually marked stock photographs,
  completed Oak's full evaluator, and saved through the game's Save menu.
  Volcano then exposed and fixed two harness defects: launch-time Z interfered
  with clean Start, and F8 was accidentally gated by the separate bounded-Z
  environment option. The corrected disarm was visually verified, and three
  ordinary apples cleared the Moltres egg. Special focus code 600 is filtered
  after it produced unusable egg frames.
- **Result:** Beach captured nine photographs across Doduo, Snorlax, Butterfree,
  Meowth, and Pidgey detector IDs. Oak accepted 3000-point Butterfree and
  Pidgey replacements plus a 40-point Meowth replacement. Tunnel captured
  Electrode, Electabuzz, Kakuna, and Zubat; Kakuna raised the report from 10 to
  11 kinds and the saved report now shows 23980 points. Host CTest is 26/26
  green. The 131072-byte FlashRAM save hashes to
  `4fd199ee17776751ef2566a37fdce3c6a1f0e185f5ef9e85143bb02b9a018aad`.
  The native link audit and PaperPad runner derivation pass, no Simulator
  was booted, and no SnapPad process remains.
- **Evidence:** `artifacts/2026-08-27/g49-auto-photo.log`,
  `artifacts/2026-08-27/g50-auto-photo.log`, the game-visible 11-kind report,
  and the rebuilt native bundle.
- **Interpretation:** end-to-end photo creation, Camera Check, Oak scoring,
  report mutation, and FlashRAM persistence now work through authentic game
  paths. River remains correctly locked by the stock 22-species threshold.
- **Next:** rerun Volcano with special-object focus filtered, select each new
  species, then target missing Beach/Tunnel species until the report reaches
  22 and require River to survive a clean production reload.

## 2026-08-27 — production iPad AOT first-play, shutter, and save reload

- **Goal:** answer the explicit mobile-readiness question with observed
  production behavior while keeping one Simulator and one game process.
- **Hypothesis:** the PaperPad-derived UIKit shell can host the same generated
  AOT core on ARM64 iOS Simulator; remaining uncertainty is launch/orientation,
  touch timing, and FlashRAM persistence rather than a missing mobile runtime.
- **Step:** built and audited `SnapPad.app` for ARM64 iOS Simulator, installed it
  on one iPad Pro 11-inch (M5) Simulator running iOS 26.5, placed the validated
  normalized ROM only in the app's private data container, and drove a fresh
  profile through title, name entry, Oak's tutorial, Beach, held viewfinder,
  and touch shutter. Recorded cadence, used the game's explicit Save flow,
  terminated the only process, relaunched the same bundle, selected Continue,
  and restored Oak's Lab. Re-ran the bundle, PaperPad parity, Apple shell syntax,
  and iOS runtime syntax audits.
- **Result:** production Metal gameplay is live on iPad; Start/A/B/D-pad and
  viewfinder/shutter inputs register, the film counter falls from 60 to 59, and
  the final 80 focused Beach samples average 59.893 input polls/s, 59.893 screen
  updates/s, and 29.928 presented frames/s. The explicit save and backup are
  matching 131072-byte FlashRAM images with SHA-256
  `82f45bdbcc866a45adeaad1bc311629d4348d51480d9a910228c8a149462d3d8`.
  Continue survives process termination and restores player `A` in Oak's Lab.
  The audited executable hashes to
  `242eee67797ea09f635d2fd80e9b503b023c348552b75f6aacd37003d53ca7e9`.
- **Evidence:** protected local files under
  `artifacts/2026-08-27/g9-ipad/`, especially screenshots 04/06/07/08/09/10,
  `11-ipad-frame-cadence.csv`, `12-ipad-production.log`, and the local protected
  FlashRAM fixture. `design-qa.md` records why exact visual comparison remains
  blocked without a PaperPad reference capture.
- **Interpretation:** iPad production first-play, touch camera input, and save
  reload are accepted at Simulator scope. G8 remains open for iPhone Simulator;
  G9 remains open for the full device/layout/lifecycle/settings matrix; G11
  still requires Chris on physical devices. This does not replace unfinished
  G6/G7 macOS progression and stability work.
- **Next:** return to the lowest unmet goal: macOS G6 progression
  from the verified 11-kind / 23980-point save.

## 2026-08-27 — production iPhoneOS build path established

- **Goal:** promote the verified mobile runtime from a Simulator-only artifact
  to the actual iPhone/iPad device SDK without weakening the existing audits.
- **Hypothesis:** the shared AOT runtime is already device-capable; the missing
  work is Xcode signing configuration, a repeatable `iphoneos` build command,
  and device-specific bundle validation rather than another emulator backend.
- **Step:** replaced the production target's forced no-sign setting with
  automatic signing and an optional development team, while retaining explicit
  unsigned Simulator builds. Added `scripts/build-ios-device.sh` with signed,
  unsigned, and auto modes and added a device-bundle audit for ARM64, iOS 15,
  native iPhone/iPad families, privacy metadata, system-only dylibs, absence of
  private inputs/paths, and signature consistency. Built the exact script twice
  against `iphoneos`; rebuilt the Simulator target and reran the host and
  PaperPad derivation checks without booting a Simulator.
- **Result:** the private unsigned device app is 9.7 MiB, targets native iPhone
  and iPad, and passes its audit. Its executable SHA-256 is
  `0bc30744c2bde93bd2416a8873f8ff9816d49b9d3bc53532163f42564849cceb`.
  The rebuilt 9.8 MiB Simulator executable hashes to
  `0989033dde15caac06fb35ce6680789c7f4d8f92496e34ba617f2d633a92f432`.
  Host CTest remains 26/26 green and no Simulator or SnapPad process was left
  running.
- **Constraint:** the current Mac reports no connected Apple device, no valid
  code-signing identity, and no configured `SNAPPAD_APPLE_TEAM_ID`. The bundle
  therefore cannot yet be signed or installed on physical hardware. Rights
  status remains private-only; no public IPA is produced.
- **Next:** boot exactly one iPhone Simulator and accept the production phone
  layout, gameplay, save/relaunch, and lifecycle paths before signed-device
  testing.

## 2026-08-27 — production iPhone gameplay and lifecycle acceptance

- **Goal:** exercise the production core on a phone-sized Apple surface and
  close the first observed phone-only input or lifecycle defect.
- **Hypothesis:** the iPad-accepted runtime and PaperPad-derived phone layout
  should transfer directly, but short touch gestures and SDL's default iOS
  audio-session behavior require observation on an iPhone.
- **Step:** booted exactly one iPhone 17 Pro Simulator on iOS 26.5, installed
  the audited production bundle, placed the validated private ROM in its app
  container, and drove title/menu input. A one-poll released analog flick was
  visible to the native bridge but could be missed between game updates, so the
  existing PaperPad flick latch was bounded to two polls and accepted as a
  one-row movement. Restored the accepted iPad FlashRAM fixture without
  conversion, continued as player `A`, entered Oak's Lab, selected Beach, and
  reached live gameplay. Then pressed Home during both opening and live course
  state and foregrounded the same process.
- **Defect:** SDL chose `AVAudioSessionCategoryPlayback` by default. Audio
  callbacks continued behind Home even though UIKit cleared held input and the
  game/render state stopped advancing.
- **Fix:** SnapPad now requests the interactive `ambient` category, pauses and
  clears queued audio on SDL background events, rejects sample queuing while
  backgrounded, and clears/restarts the device queue before controller
  reconciliation on foreground.
- **Result:** background was logged at 16.358 s and foreground at 40.156 s with
  no audio callback between them; rendering and audio resumed in the same
  process. Before/after Beach captures preserve the same rail/Pidgey state over
  a ten-second Home interval. The latest 80 focused gameplay samples average
  59.841 input polls/s, 59.841 screen updates/s, and 29.877 presented frames/s
  (25.948–30.969 range). The rebuilt Simulator executable hashes to
  `5c523f7c02fb00f330a4fd0fbd16ea72ee0be1195bb33369de0fe73258967fed`;
  the rebuilt unsigned `iphoneos` executable hashes to
  `61ee8b9834483bbe52d6c31ea64b37000c53f26ea2d1dfafac82d3b8148ecfbf`.
  Both bundle audits pass. Evidence is under
  `artifacts/2026-08-27/g9-iphone/`. The only Simulator and SnapPad process were
  terminated and the Simulator was shut down.
- **Next:** finish fresh phone name entry, multitouch shutter, settings,
  diagnostics, ROM management, controller handoff, and system interruption;
  install the signed device build when a team identity and device are present.

## 2026-08-27 — fresh iPhone name entry, tap correction, and cadence isolation

- **Goal:** close the untested fresh-phone path and determine whether the
  user-visible iPhone Simulator stutter reflects sustained rendering failure.
- **Step:** installed a save-free production bundle on the only booted iPhone
  17 Pro Simulator, imported the verified private ROM, and drove Start, New
  Game, name entry, End, and Oak's Lab through touch. Rebuilt after each input
  correction, then restored the accepted mobile save, reached live Beach, and
  left the Simulator untouched for a 45-second cadence window. Reworked the
  README against PaperPad's structure with a real ROM-free setup capture,
  target status, device instructions, controls, performance, known limits,
  diagnostics, project map, documentation, FAQ, credits, and rights boundary.
- **Defect:** PaperPad's six-poll quick-tap latch produced two photographer-name
  characters from one A tap in Pokémon Snap. A two-poll bound could still span
  two game updates depending on phase.
- **Fix:** A and Start now travel through a one-sample action edge. B, Z,
  directional inputs, and shoulders retain the original held-input path, so
  the change does not weaken camera Z hold or ordinary continuous controls.
  The PaperPad parity audit records the game-specific divergence.
- **Result:** one A tap now enters exactly one character; Start selects End and
  A confirms into Oak's Lab. The unattended Beach window averaged 59.918 input
  polls/s, 59.918 screen updates/s, and 29.937 presented fps. One interval
  dipped to 55.888/55.888/27.944 alongside a 101.385 ms audio callback gap and
  recovered immediately, identifying a short whole-process Simulator stall
  rather than sustained renderer-only loss. The final Simulator executable is
  `bdd932037c082eac0a665180312f444a3ac52ef632950a194e5091828de32f97`;
  the final unsigned device executable is
  `4e718bd418c8c9e1c2bed58d5ac5def25fb6a8d36e1b42130297a419bc01d051`.
  Both bundle audits and all 26 host tests pass.
- **Evidence:** `artifacts/2026-08-27/g9-iphone-fresh/` contains the Oak's Lab
  completion capture, cadence CSV, and matching production log. The Simulator
  app was terminated after the trace.
- **Next:** accept the remaining native settings/diagnostics/ROM-management
  paths on the same phone class, investigate interval-level pacing with a
  physical device when available, and keep the signed-device gate explicit.

## 2026-08-27 — native phone settings, diagnostics, and ROM management accepted

- **Goal:** finish the locally testable native iPhone shell paths without
  deleting or transmitting private game data.
- **Step:** installed the rebuilt bundle over the existing app container on the
  only iPhone 17 Pro Simulator, preserving the ROM and saves. Rechecked volume,
  Auto/2x resolution, original/fill aspect, touch enablement, and opacity in the
  native sheet; restored 100%, Auto, Original (4:3), controls on, and 70%. Opened
  diagnostics through the app menu and inspected the generated local report,
  then opened and dismissed installed-ROM management without choosing Replace
  or Remove.
- **Defect:** diagnostics inherited PaperPad's 40 MiB ROM-size predicate, so a
  valid 16 MiB Pokémon Snap ROM was incorrectly reported as absent.
- **Fix:** the diagnostic predicate now requires Pokémon Snap's exact 16 MiB
  size. The PaperPad shell-parity audit normalizes and requires this deliberate
  game-specific difference.
- **Result:** the report says `ROM installed: yes`, includes renderer-confirmed
  Auto at 6.00x / 1920x1440, and still excludes ROM/save contents. The system
  share sheet presents the local text report, and ROM management offers Replace
  and Remove while retaining the private-data warning. No share destination was
  chosen and no game data changed. Final executable SHA-256 values are
  `bdd932037c082eac0a665180312f444a3ac52ef632950a194e5091828de32f97`
  (Simulator) and
  `4e718bd418c8c9e1c2bed58d5ac5def25fb6a8d36e1b42130297a419bc01d051`
  (unsigned iPhoneOS).
- **Evidence:** `artifacts/2026-08-27/g9-iphone-fresh/04-iphone-diagnostics-share-sheet.png`
  (`704da9f5f6481db1a832dd18f5733c9894ad334e5d0559e3c6ba2a9015f7dd67`)
  and `05-iphone-rom-management.png`
  (`a93f983831a9710732cb1249d70147466b600529156f02584f8ab3abfda3d42c`).
- **Next:** close the physical-style phone multitouch shutter, controller
  handoff, system interruption, actual replacement, signed-device, and soak
  gates; do not infer physical-device performance from Simulator cadence.

## 2026-08-27 — phone shutter chord locked at the input boundary

- **Goal:** reduce the untested part of the phone multitouch shutter path
  without misrepresenting sequential mouse events as two-finger acceptance.
- **Step:** extended the host touch-latch regression with the exact iOS snapshot
  contract: raw held Z is ORed with a one-sample pulsed A, then Z remains held
  after A is consumed and disappears when released. Added the corresponding
  one-sample Start assertion.
- **Result:** the focused test passes and proves the corrected A-edge behavior
  cannot break the Z+A camera chord at the bridge boundary. A real simultaneous
  native-touch observation remains open because Simulator mouse input is
  single-pointer and no connected physical controller/device is available.
- **Next:** accept the chord with two physical touches on iPhone/iPad, and use a
  connected paired controller to close overlay hiding, ownership, disconnect,
  and reconnect behavior.

## 2026-08-27 — full phone ROM replacement and cold relaunch accepted

- **Goal:** exercise the installed-ROM replacement path end to end using the
  user-supplied verified ROM while preserving all private state.
- **Step:** staged `ref/pokemonsnap/build/pokemonsnap.z64` in the only iPhone
  Simulator's local Files provider, selected it through Settings → Manage Game
  ROM → Replace ROM, and cold-relaunched the rebuilt application. Compared the
  installed ROM, runtime copy, primary save, and backup save before and after.
- **Defects:** the inherited result alert was attached while UIKit dismissed the
  document picker and could disappear; the picker could leave the landscape-only
  Simulator scene portrait; Remove ROM targeted PaperPad's filename adaptation
  rather than SnapPad's actual `pokemonsnap.n64.us.z64` runtime copy.
- **Fix:** result presentation now waits for picker dismissal, both picker exit
  paths request the landscape scene geometry, and removal uses the actual runtime
  filename. These deliberate PaperPad shell hardenings are parity-audited.
- **Result:** the visible `ROM Verified` alert appears in landscape. Cold launch
  registers Pokémon Snap US and resumes the preserved game. Both ROM copies hash
  to `a1d5d816db7f8557ee04c35a011326d058b2c1fbca76b57b352b1d705a1ec1cc`;
  both 131072-byte saves remain
  `82f45bdbcc866a45adeaad1bc311629d4348d51480d9a910228c8a149462d3d8`.
  The final Simulator/device executables are
  `bdd932037c082eac0a665180312f444a3ac52ef632950a194e5091828de32f97`
  and `4e718bd418c8c9e1c2bed58d5ac5def25fb6a8d36e1b42130297a419bc01d051`.
- **Evidence:** `artifacts/2026-08-27/g9-iphone-fresh/07-iphone-rom-replacement-confirmation.png`
  (`09b5d0119e31819f0b88c86f6d50c8f10cd407894d1027f821cb56ed6798b23e`).
  The two temporary Simulator Files copies were moved to Trash after import.
- **Next:** complete physical multitouch, controller handoff, system interruption,
  signed-device, and soak gates.

## 2026-08-27 — G6 progression resumed from the accepted 13-species save

- **Goal:** resume the lowest unmet technical goal after mobile bring-up and
  advance the authentic report toward the stock 22-species River unlock.
- **State:** no Simulator or SnapPad process was running. The normalized and
  rebuilt ROMs still match; the macOS primary/backup 131072-byte saves both
  hash to `83c74935252dc51a414d04af8ec7d55b306c1e108bb35aa6d111975e940b262f`.
  The current macOS executable hashes to
  `fc111e65067d6b112fd221bd5a6e6dd49d7cffd23d8310658d2b6de7b1190267`.
- **Safety:** copied both save files to
  `artifacts/2026-08-27/g6-progression-resume/` before any game-visible write.
- **Step:** run production Continue, target missing species through real course
  input and the opt-in shutter harness, complete stock Camera Check/Oak scoring,
  save explicitly, then require River to survive a clean production relaunch.

## 2026-08-27 — Magmar advanced G6 and iPhone telemetry overhead removed

- **Goal:** keep advancing the authentic macOS report while investigating the
  user's visible iPhone 17 Simulator frame drops.
- **Progression:** a real Volcano photograph of Magmar passed through stock
  Camera Check and Professor Oak's evaluator for 1500 points. The report moved
  from 13 kinds / 29980 points to 14 kinds / 32980 points and was explicitly
  saved. The protected primary save hashes to
  `74a889ccf55d200dedf81732b4967aa940a18a95784df9f52add6a36b3fc744d`;
  the game's rotating backup was also preserved under
  `artifacts/2026-08-27/g6-progression-resume/`.
- **Harness finding:** the unique-subject shutter already de-duplicated species,
  but its sweep stopped whenever any previously captured species remained in
  focus. It now continues scanning past captured subjects while still pausing
  for an uncaptured stock detector ID.
- **Performance finding:** ordinary production audio still performed a
  per-output-frame discontinuity scan and emitted a large telemetry record every
  two seconds. That work is now opt-in behind `SNAPPAD_AUDIO_TRACE`; lightweight
  frame cadence tracing remains independently available.
- **Verification:** the rebuilt iPhone 17 Pro Simulator app ran live Beach with
  audio telemetry absent. The contiguous 48-bucket gameplay band averaged
  59.963 input/s, 59.963 screen updates/s, and 29.971 presentations/s. Short
  whole-process stalls still occurred and recovered immediately, so the
  logging work was overhead but not the demonstrated root cause. The rebuilt
  Simulator executable hashes to
  `c974d2ca99c1bacd528ab24a14e07bc3665ff8ecbe2035cf14f0c89d935f8c2a`.
- **Quality:** PaperPad runner derivation, both Apple builds, the iOS bundle
  audit, and all 26 host tests pass. The only Simulator was shut down and no
  SnapPad process remains.
- **Next:** relaunch macOS from the 14-kind save with the corrected sweep, target
  Pikachu and later Tunnel subjects, then continue toward the stock 22-kind
  River unlock. Add per-present interval telemetry and run a physical-device
  comparison when hardware is connected.

## 2026-08-27 — 17-kind save protected and successful-present pacing instrumented

- **Goal:** preserve the latest authentic G6 result, then replace inferred
  iPhone frame-rate diagnosis with interval-level evidence from RT64's actual
  presentation boundary.
- **Progression:** the corrected sweep completed another stock Camera Check and
  Oak scoring pass, advancing the report from 14 kinds / 32980 points to 17
  kinds / 41980 points. The result was explicitly saved before the gameplay
  harness closed. Protected primary and rotating-backup copies are
  `artifacts/2026-08-27/g6-progression-resume/07-after-17-species-save.bin`
  (`4557fd7637d068eaf0015640519e4e1c1a5b7c45f717fa14f8ec3a8a13cb3c26`)
  and `.bin.bak`
  (`b9a35c9fbd82cf31183e8e9d57d6d210acd46d89539372e393da0ec7992e25b6`).
- **Instrumentation:** RT64 now aggregates the count, total duration, maximum
  duration, and over-50/over-100-ms counts for intervals between successful
  `swapChain->present` calls. `SNAPPAD_PERF_TRACE_PATH` consumes those counters
  once per second without allocating or logging on the present thread. The
  change is replayable through
  `port/patches/rt64/present-interval-telemetry.patch`. The dependency-free
  `scripts/summarize_perf_trace.py` now produces weighted, range-selectable
  summaries from the checked-in CSV schema; its focused regression passes.
- **Production cleanup:** the initial UIKit/Metal geometry snapshot remains;
  the five delayed diagnostic probes now require `SNAPPAD_WINDOW_TRACE`, so
  normal gameplay no longer performs those repeated main-window/layer queries.
- **Verification:** the macOS and ARM64 iOS Simulator builds succeed, the
  Simulator bundle audit passes, PaperPad runner derivation passes, and all 26
  original host tests plus the new cadence-summary regression pass (27/27).
  The current Simulator executable hashes to
  `f3ef6a4328ac8d72da234039ed8f3eb48b60c369a22eadd09420ea70e2b5052b`.
  A production iPhone launch emitted exactly one ordinary geometry diagnostic.
- **Benchmark boundary:** a planned Auto-versus-2x Beach comparison was rejected
  after the Mac reached extreme sustained load from an unrelated multi-worker
  compile and emulator job. The contaminated traces are retained under
  `artifacts/2026-08-27/g10-iphone-present-pacing/` and explicitly labeled
  invalid; they are not application performance evidence. SnapPad was
  terminated rather than competing with that workload.
- **Next:** once unrelated host pressure clears, run the same untouched Beach
  interval at Auto and fixed 2x on the only booted iPhone Simulator, record
  active host load with each trace, and change the mobile default only if the
  controlled result demonstrates a rendering-resolution bottleneck.

## 2026-08-27 — PaperPad-to-SnapPad iPad visual parity accepted

- **Goal:** replace the prior source-only touch-shell judgment with a direct
  reference-versus-implementation comparison at one matched Apple viewport.
- **Step:** booted only the iPad Pro 11-inch (M5) Simulator, installed and ran
  the pinned PaperPad production AOT bundle against its preserved private
  container, rotated the Simulator shell to the app's landscape scene, and
  captured its inactive 70%-opacity overlay. PaperPad was terminated before
  the current SnapPad Simulator bundle was installed and launched against its
  separate preserved container. SnapPad was captured at the same 850x663
  Computer Use viewport and 1210x834-point UIKit bounds.
- **Result:** the combined PaperPad-left/SnapPad-right image shows matching
  analog, D-pad, A/B/Z, C-buttons, shoulders, Start, utility button, strokes,
  colors, opacity, spacing, scale, and safe-area placement. The two centered
  Original (4:3) viewports also align. Different game imagery is outside the
  shell comparison. The existing six-source parity audit remains green.
- **Evidence:**
  `artifacts/2026-08-27/g11-paperpad-visual-parity/06-paperpad-left-snappad-right-computer-use.png`
  (`ac3bf5bbb0c28ff84f7406fa09136db536a5bbbf0a954c48fd8cc1486de96cf2`)
  contains both captures in a single comparison input. Individual hashes and
  viewport details are recorded in `design-qa.md`.
- **Next:** terminate SnapPad and shut down the only Simulator, then return to
  the clean iPhone frame-pacing comparison after unrelated host contention
  ends.

## 2026-08-27 — iPhone Auto is not the demonstrated frame-pacing bottleneck

- **Goal:** test the user's suspected iPhone Simulator drops against one
  concrete app variable rather than changing rendering defaults by intuition.
- **Boundary:** the ten-worker unrelated compile ended before the accepted
  comparison. A separate unrelated emulator process remained stable at roughly
  one CPU core for both runs, so the result is a matched Auto-versus-2x A/B and
  not an idle-host or physical-device performance claim.
- **Step:** on the only iPhone 17 Pro Simulator, ran the same untouched Beach
  opening from the same preserved save for 45 seconds at fixed 2x / 640x480,
  then set Auto, cold-relaunched, returned through Continue and Oak's Lab, and
  repeated the same course band at the renderer-confirmed 6x / 1920x1440.
- **Result:** fixed 2x averaged 60.020 input polls/s, 60.042 screen updates/s,
  26.956 successful presentations/s, and 37.122 ms between presentations. Auto
  averaged 59.915 / 59.915 / 28.043 and 35.672 ms. Fixed 2x recorded 143 of
  1218 intervals above 50 ms; Auto recorded 104 of 1267. Auto had two isolated
  intervals above 100 ms, so the long tail remains open, but reducing internal
  resolution did not improve aggregate pacing.
- **Decision:** keep PaperPad's Auto default. The available evidence does not
  identify 6x rendering resolution as the cause of the reported drops. Continue
  to treat Simulator host contention separately and require a physical-device
  trace before changing production quality or cadence policy.
- **Evidence:** the two protected CSV traces and production logs are under
  `artifacts/2026-08-27/g10-iphone-present-pacing/`; hashes and full interval
  counts are recorded in `docs/PERF.md`. SnapPad was terminated, Auto remains
  selected, and the only Simulator was shut down.
- **Next:** rebuild and audit the unsigned `iphoneos` bundle with the new
  interval telemetry, then continue physical-controller/interruption and
  signed-device acceptance when hardware and signing are available.

## 2026-08-27 — Telemetry-current iPhone/iPad device bundle audited

- **Goal:** prove that the current successful-present telemetry and production
  cleanup compile into the real iPhone/iPad target, rather than relying on the
  Simulator build as a proxy.
- **Step:** ran `scripts/build-ios-device.sh --unsigned`, which reverified the
  pinned inputs and generated evidence, replayed the maintained patch stack,
  built Release against the iPhoneOS 26.5 SDK for ARM64 and iOS 15.0+, and ran
  the device package audit. Re-ran both mobile bundle audits, PaperPad shell
  parity, runner derivation, source-pin verification, repository safety, and
  the complete host regression suite.
- **Result:** the 9.7 MiB `SnapPad.app` is ARM64-only, identifies as
  `com.chrissotraidis.snappad`, supports iPhone and iPad, contains no ROM/save,
  private path, signing secret, or non-system runtime dependency, and passes
  the unsigned device audit. Its executable SHA-256 is
  `5d007cdeab9e27b360d0797c9e3db9e97b766a0c4fd3a28a2eb9d838703e6403`.
  The current audited Simulator executable SHA-256 is
  `c974d2ca99c1bacd528ab24a14e07bc3665ff8ecbe2035cf14f0c89d935f8c2a`.
  All 27 host tests pass; repository safety and `git diff --check` pass.
- **Boundary:** the device bundle is intentionally unsigned because this Mac
  currently has no Apple Development identity, no team ID is configured, and
  no physical device is connected. The build proves device compilation and
  package hygiene, not hands-on G11 acceptance.
- **Next:** return to the lowest unmet progression/stability gates using the
  protected 17-kind save while keeping the physical-device gate ready for the
  first available signed-device session.

## 2026-08-27 — Passive progression sweep retired; native cadence remains stable

- **Goal:** determine whether one bounded course pass could advance the
  protected 17-kind report without turning G6 into exhaustive species-by-species
  inspection.
- **Step:** ran one authentic Tunnel course and one Beach course through the
  stock detector, shutter, Camera Check, and Oak review paths. The Tunnel pass
  produced only already-reported Electrode/Magnemite frames; the Beach pass
  produced already-reported Pidgey, Doduo, Lapras, Snorlax, Meowth, and
  Kangaskhan frames. A final targeted Beach observation confirmed that simple
  repeated horizon sweeps are exhausted and returned to the lab without a save
  write.
- **Decision:** stop passive repetition. The remaining stage-2 progress needs
  ordinary item/interaction routes and later courses, not checking every
  character or accumulating duplicate photos. No production rule or score was
  changed.
- **Safety:** both 131072-byte FlashRAM files remain byte-for-byte equal to the
  protected 17-kind state: primary
  `4557fd7637d068eaf0015640519e4e1c1a5b7c45f717fa14f8ec3a8a13cb3c26`
  and backup
  `b9a35c9fbd82cf31183e8e9d57d6d210acd46d89539372e393da0ec7992e25b6`.
  Every SnapPad process exited normally and no Simulator was booted.
- **Performance:** the 199-bucket native Beach band held 59.998 input and
  screen updates/s and 29.971 successful presentations/s, with a 33.380 ms
  mean interval, 97.077 ms maximum, and no interval above 100 ms. Full details
  are recorded in `docs/PERF.md`; this does not replace the 60-minute soak.
- **Next:** use the stock interaction/item route to unlock the next course, and
  spend engineering time on observable progression, audio, rendering, and
  stability defects rather than duplicate report coverage.

## 2026-08-27 — Targeted Rapidash result protected; stage-2 rule traced

- **Goal:** replace broad subject/photo grinding with the minimum authentic
  progression work needed to reach River.
- **Rule evidence:** the stock photo-check progression code unlocks River at 22
  reported species. Apple requires 24000 report points after stage 0; Pester
  Ball requires 72500 points at stage 3 or later. The current release route
  therefore needs four more distinct report subjects, not exhaustive coverage.
- **Progression:** a Volcano pass produced a new Rapidash photograph through
  the ordinary shutter, Camera Check, and Professor Oak evaluation paths. Oak
  advanced the report from 17 kinds / 41980 points to 18 kinds / 44980 points
  and explicitly reported that four more pictures remain before the next
  course. The result was explicitly saved and SnapPad exited normally.
- **Safety:** primary and rotating-backup FlashRAM are both 131072 bytes and
  byte-for-byte equal. Protected copies are
  `artifacts/2026-08-27/g6-stage2-targeted/04-after-18-species-save.bin` and
  `.bin.bak`, both SHA-256
  `2d5e827d17d968e4dcae7a564c80e817b55adb83f05179acaa5d46e34b953dab`.
- **Test-harness decision:** the opt-in vertical camera sweep drove the view
  into terrain and reduced useful coverage, so it was removed. The existing
  horizon sweep remains test-only; no production input or game rule changed.
- **Verification:** the native macOS app and unsigned ARM64 iPhone/iPad bundle
  rebuild successfully. All 27 host tests, the native app audit, unsigned
  device audit, repository safety, and `git diff --check` pass. Current macOS
  and iPhoneOS executable SHA-256 values are respectively
  `93797850fac77a9bb9a51bbae3f01d0ec99a8323a461f6ec601dc927fbf8b94d`
  and
  `fa76336032ab74da43f6b3082542885cf04e4c279af045ea709547c268b55c86`.
- **Next:** target four known missing subjects through their ordinary course
  interactions, then accept the River unlock and continue G6. Keep the
  physical-device and 60-minute soak gates open.
- **Bounded follow-up:** one cleaned Tunnel pass focused only Electrode (101),
  Electabuzz (125), Kakuna (14), and Magnemite (81), all already present in the
  protected report. The duplicate roll was rejected without Oak submission or
  a save write; primary, backup, and protected-copy hashes remain exactly
  `2d5e827d17d968e4dcae7a564c80e817b55adb83f05179acaa5d46e34b953dab`.
  This confirms the next pass must deliberately perform a missing subject's
  stock interaction rather than repeat a passive sweep.

## 2026-08-27 — Bounded Volcano pass advanced the report to 19 species

- **Scope:** run one instrumented Volcano course, not an exhaustive subject
  audit. The pass was limited to proving that one ordinary capture can still
  traverse Camera Check, Oak evaluation, explicit FlashRAM save, and clean
  process exit.
- **Interaction result:** the test-only input helper found the Moltres egg and
  emitted ordinary apple-button pulses, but Moltres did not appear. The helper
  was not retried unchanged and was removed from the runner and its PaperPad
  derivation transform after the pass.
- **Progression result:** the existing stock-detector shutter path captured a
  genuinely new Charmeleon in the same course. Camera Check marked it `NEW`,
  Oak accepted it for 3000 points, and the report advanced from 18 kinds /
  44980 points to 19 kinds / 47980 points. Three distinct report subjects now
  remain before the stock River unlock at 22.
- **Save evidence:** the result was explicitly saved, returned to the title,
  and SnapPad quit normally. The protected primary FlashRAM copy is
  `artifacts/2026-08-27/g6-stage2-targeted/17-after-19-species-save.bin`
  (131072 bytes, SHA-256
  `bb4ddc6ef059d2412f6c1a0cd0f9ddcbe6ff66ae782032e39806eeb0b8edbd60`).
  Its rotating backup preserves the preceding 18-species state at SHA-256
  `2d5e827d17d968e4dcae7a564c80e817b55adb83f05179acaa5d46e34b953dab`.
- **Regression:** the PaperPad runner derivation audit, native macOS bundle
  audit, unsigned ARM64 iPhone/iPad bundle audit, repository safety checks,
  `git diff --check`, and all 27 host tests pass. Current macOS and iPhoneOS
  executable SHA-256 values are respectively
  `f1d568fb6ddc28e225a277c9f3a814c73819cda73a478cb64b42bcf4d20d9aaa`
  and `ce0f7638a559e3ed45621c72922f454d2fd2a357da5b191dbb34d48349f08992`.
- **Performance note:** the full acceptance trace includes gameplay, Camera
  Check, Oak scoring, and menus, so its aggregate 38.624 presented fps is not
  a gameplay-framerate measurement. The established gameplay baseline remains
  approximately 30 fps with near-60 Hz input/screen updates; phone Simulator
  stalls still require physical-device comparison.

## 2026-08-27 — Moltres timing run bounded; save remained protected

- **Scope:** one evidence-corrected Volcano attempt from the protected
  19-kind save. The run targeted only the stock Moltres egg interaction and
  rejected every duplicate photo; it did not scan the report character by
  character or alter production game rules.
- **Result:** the viewfinder observed the egg's special focus code 600, but the
  manual apple sequence arrived after the useful collision window. The intact
  egg then blocked the Neo-One at the stock Volcano fork until the course was
  quit. Camera Check contained only Rapidash, Vulpix, Charmander, and Magmar,
  all already reported. This was expected game progression behavior, not an
  application hang, and the failed timing is not being repeated unchanged.
- **Save safety:** no picture was submitted to Oak and no save was requested.
  The 131072-byte primary remains SHA-256
  `bb4ddc6ef059d2412f6c1a0cd0f9ddcbe6ff66ae782032e39806eeb0b8edbd60`;
  the rotating backup remains
  `2d5e827d17d968e4dcae7a564c80e817b55adb83f05179acaa5d46e34b953dab`.
  SnapPad exited normally and no Simulator device was booted.
- **Frame cadence:** the 277.958-second gameplay band held 60.013 input polls/s,
  60.013 screen updates/s, and 29.997 successful presentations/s. Its maximum
  presentation interval was 110.748 ms, with one interval over 100 ms. The
  much lower full-run aggregate includes long menus, Camera Check, and the
  intentionally blocked course state and is not a gameplay-framerate result.
- **Next:** pivot to a different missing subject or a tighter event-driven egg
  interaction. Do not use another long wall-clock delay after focus code 600.

## 2026-08-27 — Repetitive subject probing stopped; device build refreshed

- **Decision:** stop treating each report subject as an exhaustive search
  problem. A temporary event-driven Moltres experiment failed to produce a
  usable stock photograph and was removed completely from the runner and its
  PaperPad derivation transform. It is not part of SnapPad.
- **Bounded Tunnel result:** one first-Diglett route was attempted using only
  ordinary input. The camera correction missed the block-three appearance
  window, and the resulting roll contained only already-reported species. The
  roll was rejected without Oak submission or a save write; this route will
  not be repeated unchanged.
- **Save safety:** the 19-species primary remains SHA-256
  `bb4ddc6ef059d2412f6c1a0cd0f9ddcbe6ff66ae782032e39806eeb0b8edbd60`;
  its rotating backup remains
  `2d5e827d17d968e4dcae7a564c80e817b55adb83f05179acaa5d46e34b953dab`.
- **Cadence:** the actual 139-second Tunnel gameplay band averaged 60.029 Hz
  input, 60.029 Hz screen updates, and 30.011 presented fps. The observed
  ranges were 58.941–60.939 Hz for input/screen updates and 28.827–30.938 fps
  for presentation, with no presentation interval over 100 ms.
- **Device build:** the clean production core rebuilt as an audited, ROM-free,
  unsigned 9.7 MiB ARM64 `iphoneos` app. Its executable SHA-256 is
  `ce0f7638a559e3ed45621c72922f454d2fd2a357da5b191dbb34d48349f08992`.
  It remains intentionally un-installable until an Apple Development identity,
  team, and physical device are available.

## 2026-08-27 — Native 60-minute stability soak completed

- **Scope:** validate sustained process, cadence, audio-queue, transition, and
  resident-memory behavior without another exhaustive subject search. Exactly
  one ARM64 macOS SnapPad process ran; no Simulator was booted.
- **Route:** loaded the protected Continue save and completed 14 natural
  Beach-to-Oak's-Lab return cycles in one uninterrupted 60-minute process.
  Empty rolls correctly bypassed photo review. A keyboard shutter experiment
  did not consume film and is not claimed as photo-path coverage.
- **Cadence:** the 3,599-bucket mixed-state trace held 59.954 Hz input and
  59.962 Hz screen updates. A representative uninterrupted 152-second course
  band presented at 30.005 fps with no interval over 100 ms. Whole-run
  presentation averages are not gameplay FPS because they include menus,
  loading, transitions, and UI-control observations.
- **Audio and memory:** all 1,799 audio records reported zero conversion errors,
  zero queue errors, and no queue depth over 100 ms. In the final 30 minutes,
  RSS moved from 128,224 to 127,408 KiB with a -134 KiB/min least-squares
  slope; repeated post-course releases show no sustained growth.
- **Shutdown and save safety:** after 60 minutes SnapPad handled `SDL_QUIT` and
  exited normally. The primary save remains
  `bb4ddc6ef059d2412f6c1a0cd0f9ddcbe6ff66ae782032e39806eeb0b8edbd60`;
  its backup remains
  `2d5e827d17d968e4dcae7a564c80e817b55adb83f05179acaa5d46e34b953dab`.
- **Evidence:** `artifacts/2026-08-27/g7-macos-soak/22-cadence.csv`,
  `23-runtime.log`, and `24-memory.csv`. Native duration is now covered; photo
  review, broader course transitions, and signed physical-device stability
  remain open.

## 2026-08-27 — Blind progression sweeps replaced with save-derived targets

- **Goal:** advance G6 without inspecting menus or repeating whole courses for
  species already present in the report.
- **Method:** added the read-only `scripts/inspect_snap_save.py` tool from the
  pinned decomp's `UnkBigBoy` offsets and exact 63-slot `D_800AE4E4` roster.
  It validates the 128 KiB FlashRAM size and `HAL_SNAP_V1.0-1` marker, reads
  report-presence and score fields, and never writes its input.
- **Result:** the protected save independently resolves to 19 reported species
  and 47,980 points, exactly matching the game-visible report. The roster
  confirms that prior passive captures already cover Rapidash, Kakuna,
  Magnemite, and the other repeatedly observed duplicates. Missing candidates
  in unlocked courses are now explicit, so only a deliberate stock interaction
  for one of them is justified.
- **Regression:** two synthetic-save tests cover roster/score decoding,
  read-only behavior, wrong-size rejection, and version rejection. The full
  host suite is 29/29 green.
- **Next:** make one bounded course attempt at an actually missing, ordinary
  target—prefer Eevee on Beach or Charizard in Volcano—then inspect the save
  once after Oak submission rather than scanning every screen or subject.

## 2026-08-27 — Save-informed Eevee attempt bounded after one course

- **Scope:** exactly one Beach pass targeting missing Eevee (133), with no
  report-screen crawl and no repeat after the same route missed.
- **Observed route:** the stock detector and ordinary shutter created seven
  photographs: Doduo, Lapras, Snorlax, Butterfree, Pidgey, Meowth, and
  Kangaskhan. Eevee never entered detector focus, so the route did not claim a
  target hit.
- **Disposition:** all seven subjects were already present in the save-derived
  report roster. Camera Check was disarmed and exited without marking a photo;
  nothing went to Oak and no save was requested. SnapPad returned to the lab
  and logged `SDL_QUIT received` on normal exit.
- **Integrity:** the read-only inspector still reports 19 species / 47,980
  points. Primary and backup hashes remain respectively
  `bb4ddc6ef059d2412f6c1a0cd0f9ddcbe6ff66ae782032e39806eeb0b8edbd60`
  and `2d5e827d17d968e4dcae7a564c80e817b55adb83f05179acaa5d46e34b953dab`.
- **Cadence:** the 424.687-second mixed-state trace held 59.905 Hz input and
  59.974 Hz screen updates. Its aggregate 35.381 presentations/s includes
  title, lab, course, and Camera Check and is not a gameplay-framerate claim.
- **Evidence:** `artifacts/2026-08-27/g6-eevee-target/01-runtime.log`,
  `02-photo-score.log`, and `03-perf.csv`. No Simulator was booted.
- **Next:** do not repeat the Beach sweep. Pivot to a bounded Volcano Charizard
  interaction, which is missing from the report and uses ordinary apple input.

## 2026-08-27 — Charizard dependency bounded; Diglett advances River unlock

- **Charizard finding:** the pinned decomp shows that Charizard is spawned only
  after the late-course Charmeleon is knocked onto the lava surface. The intact
  Moltres egg stopped the Neo-One before that encounter. Because the earlier
  egg timing route had already failed at the same geometry, this pass ended
  without repeating it, submitting a photo, or writing the save.
- **Charizard cadence:** the 458.802-second mixed-state trace held 59.943 Hz
  input and 60.008 Hz screen updates. Its aggregate 32.652 presentations/s
  includes menus and course transitions; no present interval exceeded 100 ms.
  Evidence is in `artifacts/2026-08-27/g6-charizard-target/`.
- **Tunnel result:** the next bounded ordinary Tunnel pass produced six photos.
  The save-derived roster identified Diglett as the only new subject, so the
  automated shutter was immediately disarmed and only Diglett was marked in
  Camera Check. Oak recognized Diglett and awarded 1,000 size + 500 pose,
  doubled by centered technique, for 3,000 points.
- **Progression:** the visible report advanced from 19 kinds / 47,980 points to
  20 kinds / 50,980 points, and Oak explicitly said two more pictures remain
  before the next course. The trip was explicitly saved before returning to
  the title screen and quitting through SDL.
- **Integrity:** `scripts/inspect_snap_save.py` independently confirms Diglett
  at 3,000 points in a 20/63-species, 50,980-point protected save. The primary
  SHA-256 is
  `27c2575ee4ba820f7ab559bd9306c3586a7466f902f57f8597d04c3f487ec2ec`;
  the backup is the prior primary,
  `bb4ddc6ef059d2412f6c1a0cd0f9ddcbe6ff66ae782032e39806eeb0b8edbd60`.
- **Cadence:** the 694.700-second mixed-state Tunnel/photo-review trace held
  59.955 Hz input and 60.000 Hz screen updates. Its aggregate 43.194
  presentations/s spans lab, gameplay, Camera Check, scoring, save, and title,
  so it is not a gameplay-framerate claim.
- **Evidence:** `artifacts/2026-08-27/g6-haunter-target/01-runtime.log`,
  `02-photo-score.log`, and `03-perf.csv`. No Simulator device was booted.
- **Next:** use the protected 20-kind save for two bounded missing-subject
  captures, accept River at the stock 22-species threshold, then continue G6.

## 2026-08-27 — Blind follow-ups stopped after bounded misses

- **Tunnel:** one Dugtrio-oriented sweep and one phase-shifted Haunter sweep
  each completed exactly once. Neither missing subject entered detector focus;
  all captured subjects were already reported, so neither run submitted a
  photo to Oak. Both processes logged `SDL_QUIT received`.
- **Beach:** stock-route research confirmed that ordinary Pokémon Food can
  reveal the pink rolling Chansey disguise. The first bounded pass found the
  ball visibly but armed the shutter after its collision window. A refined
  pass kept normal item input and located the encounter area again, but still
  missed the short item/camera overlap; its lone duplicate Pidgey was rejected.
- **Integrity:** the read-only inspector remains authoritative at 20/63 species
  and 50,980 points. Returning from the Gallery caused one metadata-only save
  rewrite: current primary SHA-256 is
  `136e183d20659bdbd381e668d060f26c3343c7344fbb4e9abdd6dc5da45bf745`,
  and the Diglett progression save is now the backup at
  `27c2575ee4ba820f7ab559bd9306c3586a7466f902f57f8597d04c3f487ec2ec`.
- **Cadence:** the Dugtrio, Haunter, and Chansey mixed-state traces kept
  59.938–59.963 Hz input and 60.003–60.017 Hz screen updates. Their aggregate
  presentation rates span menus, courses, and review and are not gameplay-fps
  claims; no successful-present interval exceeded 100 ms.
- **Evidence:** `artifacts/2026-08-27/g6-dugtrio-target/`,
  `g6-haunter-target-2/`, and `g6-chansey-target/`.
- **Decision:** do not spend more time varying manual sweep phase or polling
  every screen. The next progression work must derive a deterministic stock
  event/aim cue for one missing subject, then make one evidence-producing pass.

## 2026-08-28 — Stock item-impact cue replaces visual timing guesses

- **Runtime cue:** the command observer now retains the target Pokémon ID only
  for the stock pester-impact and apple-impact commands. A single-consumer hook
  passes that authenticated event to the input runner, where the opt-in
  `SNAPPAD_TEST_AUTO_SHUTTER_ARM_ON_ITEM_SUBJECT` route can arm the existing
  ordinary shutter for one exact subject. Normal launches set none of these
  test variables and retain the production input path unchanged.
- **Coverage:** host tests prove that apple impact publishes subject 113,
  proximity does not count as impact, consumption is single-use, and session
  reset clears a pending event. The audited PaperPad-derived runner block was
  updated for the intentional input-only addition; all 29 host tests, runner
  derivation, shell parity, repository safety, and `git diff --check` pass.
- **Native evidence:** the rebuilt ARM64 app passed its bundle audit. During one
  bounded Beach run, the trace recorded two stock apple impacts on Pidgey
  (subject 16) and no impact on Chansey (subject 113). The requested cue
  therefore correctly never armed, no photograph reached Oak, and the app quit
  through SDL. Evidence is in
  `artifacts/2026-08-27/g6-chansey-impact-cue/`.
- **Integrity:** the report remains 20/63 species and 50,980 points. Primary
  SHA-256 remains
  `136e183d20659bdbd381e668d060f26c3343c7344fbb4e9abdd6dc5da45bf745`;
  backup remains
  `27c2575ee4ba820f7ab559bd9306c3586a7466f902f57f8597d04c3f487ec2ec`.
- **Decision:** the event mechanism is validated, but the bounded Chansey route
  is exhausted. Progression work moves to a deterministic Diglett reappearance
  sequence for Dugtrio rather than another manually phased screen sweep.

## 2026-08-28 — Product loop reoriented to iPadOS/iOS

- **Boundary decision:** the macOS SnapPad product has passed its current QA
  boundary: native ARM64 packaging, Metal video, generated audio, input, the
  complete first-play photo/scoring path, FlashRAM save/reload, clean exit,
  measured cadence, and the 60-minute soak are all evidenced. Collecting every
  Pokémon report subject is full-game compatibility work, not a prerequisite
  for mobile product development.
- **Stopped work:** a planned repeated-Diglett acceptance input was removed
  before adoption. Two menu-desynchronized native probes exited through SDL,
  submitted nothing to Oak, and did not change the protected report or save.
  No Simulator was booted.
- **Operating change:** `docs/GOAL-LOOP.md` now uses product phases. P0
  reproducibility and P1 macOS are accepted; P2 iPadOS/iOS is active; signed
  physical-device acceptance is P3; complete-game progression remains P4; and
  publication remains explicitly gated at P5.
- **Mobile acceptance target:** match pinned PaperPad at the same iPad/iPhone
  viewport, prove real simultaneous Z-hold/A-tap touch shutter input, verify
  responsive safe-area layout, settings/ROM/diagnostics/lifecycle/controller
  behavior, capture focused cadence, and keep the ARM64 device bundle AOT-only,
  ROM-free, and auditable.
- **Next:** audit current iPad and iPhone touch surfaces against PaperPad, fix
  the highest-impact mismatch, then run one-Simulator-at-a-time acceptance.

## 2026-08-28 — Current iPhone/iPad touch audit passes visually

- **Candidate:** rebuilt the Release iOS Simulator app from current source. The
  PaperPad shell parity and iOS syntax checks passed before Xcode completed the
  ARM64 Simulator link; the ROM-free bundle audit passed.
- **Phone:** on the single iPhone 17 Pro Simulator, SnapPad resumed live native
  gameplay with the complete grip-first overlay. The settings sheet remained
  safe-area bounded, and Reset Touch Layout restored the source-defined phone
  defaults. A pinned PaperPad runtime capture on the same Simulator confirmed
  the control family and geometry; its preserved binary has the older
  top-right utility position, while the pinned source and current SnapPad both
  intentionally use the accepted top-center phone slot.
- **Tablet:** the phone process was terminated and its Simulator shut down
  before the single iPad Pro 11-inch Simulator booted. The current tablet
  landscape capture preserves the previously accepted PaperPad-derived layout.
- **Cadence limit:** a 45-second iPhone trace stayed near 60 Hz with no >50 ms
  interval after startup, but the observed band ended in a 60 Hz course
  cutscene. It is retained as transition evidence and is not claimed as a
  focused gameplay-framerate result.
- **Audit limit:** screenshots and source parity do not prove physical reach,
  VoiceOver operation of the custom-drawn controls, or simultaneous Z+A touch.
  The phone multitouch shutter remains the next interaction check. Both
  Simulators and all game processes were shut down at the end.
- **Evidence:** `design-qa.md`,
  `artifacts/2026-08-28/p2-iphone-touch-audit/`, and
  `artifacts/2026-08-28/p2-ipad-touch-audit/`.

## 2026-08-28 — Current ARM64 device candidate rebuilt and audited

- **Build:** `scripts/build-ios-device.sh --unsigned` rebuilt the current source
  for `iphoneos` and completed successfully. The resulting universal-family
  iPhone/iPad app is 9.7 MiB, ARM64-only, and targets iOS/iPadOS 15 or newer.
- **Boundary:** `scripts/audit-ios-device-bundle.sh` confirms the app is AOT-only
  and contains no ROM, save, generated source input, private path, signing
  secret, or non-system dynamic dependency. Executable SHA-256 is
  `3c01d612a854d6676a6976eaebed27ab87e86c616a4591db1506242619b66dbf`.
- **Regression:** all 29 host tests, PaperPad shell and runner audits, repository
  safety, and `git diff --check` pass after the goal-loop, status, design QA,
  and README reorientation.
- **Install boundary:** the artifact remains intentionally unsigned and cannot
  be installed until an Apple Development identity/team and connected device
  are available. Simulator visual/touch evidence does not replace that
  hands-on gate.

## 2026-08-28 — Simulator mobile product boundary accepted

- **Acceptance decision:** P2 is complete at Simulator scope. iPad has observed
  native two-finger Z-hold/A-tap shutter evidence; iPhone has current touch
  control, compact-layout, gameplay, settings, lifecycle, and cadence evidence.
  Both device classes use the same multi-touch bridge, and the input regression
  proves the held-Z plus one-sample-A mixer behavior exactly.
- **Honest boundary:** Computer Use and Simulator expose only a single pointer,
  so manufacturing a second mouse event would not establish phone grip feel.
  Exact simultaneous phone feel, physical reach, thermal behavior, and
  physical-device performance move to P3 hands-on acceptance.
- **No code churn:** the same-viewport visual audit found no PaperPad-derived
  layout defect worth changing. The preserved unsigned ARM64 `iphoneos`
  candidate remains ROM-free and audited.
- **Next:** sign and install this candidate on one connected iPhone or iPad when
  an Apple Development identity and team are available; do not resume exhaustive
  Pokémon report collection while that product gate is pending.
- **Prerequisite check:** Xcode currently sees only the host Mac plus
  Simulators, and the keychain reports zero valid code-signing identities. The
  Mac is not locked; P3 is waiting specifically for a connected iOS/iPadOS
  device and Apple Development signing setup.

## 2026-08-28 — Genuine widescreen exposed as an experiment

- **Capability:** RT64 already supports expansion of perspective projections,
  framebuffers, viewports, and fixed rectangles to the swap-chain aspect. This
  is materially different from SnapPad's existing Fill Screen final-composite
  crop. Pokémon Snap itself hardcodes 4:3 in its gameplay camera and explicitly
  forces 4:3 during photo scoring, so the enhancement cannot be the baseline.
- **Implementation:** the native Aspect Ratio control now offers Original
  (4:3), Fill Screen, and Wide (Experimental). Wide has a separate runtime
  signal that enables RT64 `aspectRatio` and `extAspectRatio` expansion; Fill
  continues to preserve 4:3 projection and crop only the final composite.
  Persisted values are bounded, diagnostics name all three modes, and the UI
  warns that Original is required for accuracy.
- **Observed result:** one iPhone 17 Pro Simulator was used. On Beach, Wide
  changed the renderer-confirmed Auto target from 1920x1440 to 3131x1440,
  filled the display with a visibly wider 3D field, kept the reticle centered,
  and preserved touch controls. Authored title, Lab, and course-selection
  screens stayed 4:3 rather than being stretched. Original was restored before
  the app was terminated and the Simulator shut down.
- **Boundary:** this proves genuine widened presentation, not photo-system
  correctness. Wide remains default-off until photo capture, subject detection,
  score composition, HUD edges, and physical-device performance are accepted.
- **Device candidate:** the post-change unsigned ARM64 `iphoneos` bundle builds
  and passes the ROM/signing/path/runtime audit. Executable SHA-256 is
  `75182baf791e263ac1865d6b4663a69edb0933d2c959a43b55ffc892deb0e373`.
- **Evidence:** `artifacts/2026-08-28/experimental-widescreen/` contains the
  Wide Beach frame and restored Original Beach frame.

## 2026-08-28 — First-run cancellation repaired and public README tightened

- **Observed defect:** on a fresh iPad Simulator install, cancelling the native
  Files picker could leave SnapPad's scene behind the previously foregrounded
  app. The setup controller updated its retry text, but its temporary `UIWindow`
  was created without the active `UIWindowScene`.
- **Repair:** first-run setup now resolves the foreground scene, constructs its
  window with `initWithWindowScene:`, and explicitly restores that window after
  picker cancellation or a rejected file. The PaperPad parity normalizer
  records this as deliberate SnapPad lifecycle hardening.
- **Current observation:** the rebuilt ROM-free app stayed foreground on an
  isolated iPad Pro 11-inch (M5) Simulator running iOS 26.5, restored
  landscape, displayed `No ROM selected`, and allowed the picker to open again.
  With the verified private ROM present, AOT Metal gameplay, the utility menu,
  settings presentation, vertical settings scrolling, and return to gameplay
  were also observed.
- **Environment limit:** an unrelated GoldenPad LAN test automation repeatedly
  launched itself on other booted iPad Simulators. Those cross-app frames were
  rejected as SnapPad evidence; the cancellation result above was repeated on
  a separate device before its private ROM was seeded.
- **Public-facing update:** the README now leads with the player outcome,
  separates install availability from technical readiness, documents the
  retryable Files flow and Simulator orientation quirk, and shows current
  first-run and settings captures without including private game data.

## 2026-08-28 — First physical iPad deployment establishes preserved state

- **Target:** the current candidate was development-signed and installed for
  the first time on an iPad Pro 12.9-inch (6th generation) running iPadOS 26.6.
  SnapPad did not previously exist on the device, so this deployment created
  the accepted persistent container rather than replacing earlier SnapPad data.
- **Signing repair:** `scripts/build-ios-device.sh --signed` could inherit the
  prior unsigned build directory's `CODE_SIGNING_ALLOWED=NO` cache and then
  misleadingly announce a signed result. Signed mode now clears that cache,
  allows Xcode provisioning updates, and fails unless both the signature and
  embedded provisioning profile exist. The signing team was taken from the
  profile's `TeamIdentifier`, not the certificate display-name suffix.
- **Private ROM:** the verified normalized Pokémon Snap US ROM was copied only
  to SnapPad's private Application Support directory with owner-only
  permissions. A device-to-host readback matched the locked SHA-1 exactly; the
  ROM-free application bundle remained unchanged.
- **Runtime:** SnapPad remained active after launch. Its device-local log
  registered the expected game core, created a native 2732×2048 Metal drawable,
  routed the first audio task through verified `aspMain`, and recorded live
  touch input. This is stronger than installation alone, but the full physical
  acceptance checklist remains open.
- **Preservation baseline:** the initial Application Support payload and current
  preferences plist were copied to ignored
  `artifacts/device-backups/2026-08-28-initial/`. Project instructions now
  require a private backup before every device update, in-place installation,
  and post-update verification of ROM, saves, and preferences. Uninstalling,
  changing the bundle identifier, or using `--remove-existing-content` requires
  explicit reset authorization.

## 2026-08-28 — v0.1.0 public release authorized

- **Decision:** after hands-on physical-iPad play, Chris accepted the current
  build as stable and explicitly authorized the first public integration-source
  snapshot, release tag, supplied title-screen image, and free unsigned ROM-free
  IPA. This supersedes the earlier private-only release decision for this exact
  scope without claiming upstream legal clearance.
- **Player path:** the README now leads with the supplied physical-iPad title
  frame directly below the platform badges, removes the rejected prior hero
  image, links the v0.1.0 IPA, and explains AltStore Classic, AltServer,
  Developer Mode, ROM import, refresh limits, and data-preserving updates in
  consumer terms.
- **Package boundary:** the new public package scripts accept only an unsigned
  ARM64 iPhoneOS app, require the privacy manifest and iPhone/iPad icon assets,
  reject ROM/save/generated/signing/private data, include the scoped rights
  notice plus pinned dependency licenses, and emit a SHA-256 checksum.
- **Honest boundary:** v0.1.0 is an unofficial free GitHub community release,
  not an App Store or TestFlight build. Dedicated physical-iPhone coverage,
  wider controller/interruption/thermal testing, full progression, and the
  decompilation/translated-code rights question remain documented work.
- **Exact artifact:** two independent packages were byte-identical. The
  7,699,951-byte `SnapPad-v0.1.0-unsigned.ipa` has SHA-256
  `37741aebff29f05263cee6a7fb146b3f76c5c75c30ccd958caeb34e5a06590df`,
  contains version `0.1.0` build `1`, 54 dependency notice files, no signature
  or provisioning profile, and no ROM, save, generated input, credential, or
  private path.
