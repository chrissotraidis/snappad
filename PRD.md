# SnapPad PRD: Pokémon Snap, native on Apple platforms

Status: approved for **gated autonomous execution**. Written 26 Aug 2026.
Audience: an autonomous agentic system with full control of a macOS Apple Silicon machine.
Companion document: `docs/GOAL-LOOP.md` (the operating loop). Read both before doing anything.

Decision: **GO for a private technical porting program. NO-GO for a public release until the technical, physical-device, package-safety, and rights gates in this document are all satisfied.**

---

## 1. Objective

Build **SnapPad** (`snappad`, working project name): a native ARM64 port of **Pokémon Snap (Nintendo 64, US revision)** for macOS, iPadOS, and iOS. The game executable is statically recompiled ahead of time with **N64Recomp**; supported RSP microcode is handled with **RSPRecomp and/or a documented runtime path**; **N64ModernRuntime** supplies the N64 operating environment; **RT64's Metal backend** supplies rendering. The user provides their own legally obtained supported ROM.

The existing repository is the game-specific source of truth for the matching decompilation, symbols, linker map, ELF, overlays, DMA behavior, controller/accessory behavior, FlashRAM behavior, and game logic. **PaperPad** is the reference Apple implementation and lives at `ref/paperpad`. Use it for the Apple shell, touch controls, controller handling, ROM import, settings, diagnostics, lifecycle, build scripts, dependency pinning, runtime patches, package audits, and evidence discipline. Treat it as read-only.

Order of delivery:

1. **Reproducible source state.** Verify the exact US ROM, rebuild the exact ROM and symbolized ELF from the repository, pin every toolchain input, and record the public-rights state.
2. **Recompilation gates.** Generate the N64Recomp output, register every executable section and overlay, validate RSP paths, validate FlashRAM, and compile/link a native macOS core.
3. **macOS first-play loop.** Title screen → new game → Professor Oak's Lab → Beach → take photographs → finish the course → photo review/scoring → save → relaunch and load.
4. **Complete macOS game path.** All courses, progression unlocks, items, report/album/gallery flows, Rainbow Cloud, credits, and stable save persistence.
5. **Native timing and correctness.** Preserve the original US game's actual VI/gameplay cadence, audio behavior, camera behavior, photo capture, and scoring. Measure; do not assume a 30 or 60 fps target from memory.
6. **iPadOS and iOS Simulator cores.** Build iPad first, then iPhone, with the same ahead-of-time game core and no runtime-generated executable code.
7. **PaperPad shell port.** Touch overlay, three-dot menu, ROM management, settings, physical-controller handling, diagnostics, lifecycle handling, and release-audit machinery adapted as SnapPad.
8. **End-to-end and physical-device acceptance.** Complete the test matrix in Section 10, then obtain hands-on iPad/iPhone evidence from Chris against the exact candidate artifact.
9. **Public release gate.** Resolve repository and dependency licensing/permission, audit the source and package boundaries, and publish nothing until Section 12 is green.

Three requirements are hard, not aspirational:

- **The first-play loop must work end to end.** A generated C directory, a successful compile, a process ID, a title screen, or a course that cannot complete is not a playable port.
- **The complete game must preserve baseline timing and progression.** Do not replace this with a reduced demo, a single-course acceptance target, or an arbitrary enhanced-framerate target.
- **A public release requires explicit rights clearance and exact-artifact testing.** “ROM-free” by itself is not legal or release clearance.

## 2. What “done” means

All of the following, each backed by evidence per Section 11:

- **D1. Exact input and rebuild.** The supplied ROM is normalized to big-endian `.z64`, matches SHA-1 `edc7c49cc568c045fe48be0d18011c30f393cbaf`, and the repository cleanly produces `build/pokemonsnap.z64`, `build/pokemonsnap.elf`, and `build/pokemonsnap.map`. The rebuilt ROM matches the expected checksum.
- **D2. Recompilation coverage.** N64Recomp and RSPRecomp complete from the pinned toolchain; generated output compiles and links for macOS; every executable section that can be loaded has a recorded overlay identity and runtime registration; no unresolved function lookup, executable-range write, unsupported RSP overlay, or silently skipped code region remains.
- **D3. macOS first-play loop.** The packaged macOS app boots through the title and new-game flow, reaches Oak's Lab, completes Beach, takes and stores photographs, reaches Oak's photo review, produces plausible scoring, writes FlashRAM, exits cleanly, relaunches, and restores progress, with working video, input, music, and sound effects.
- **D4. Complete macOS progression.** A fresh-save golden path completes Beach, Tunnel, Volcano, River, Cave, Valley, Rainbow Cloud, and credits with the expected unlocks and no progression blocker. Pokémon Report, Album, Gallery, course selection, item unlocks, and later-game camera interactions work.
- **D5. Native timing and correctness.** Original US timing/cadence is measured and documented. Frame pacing, audio pitch/continuity, input response, course scripting, photo capture, Pokémon detection, and score calculation stay within the measured baseline. Performance claims are backed by profiles, not adjectives.
- **D6. Simulator core.** iPadOS Simulator and iOS Simulator builds boot through the first-play loop with the same AOT core. Simulator performance is recorded as diagnostic evidence only; it is not physical-device acceptance.
- **D7. Apple shell.** PaperPad's touch controls, controller behavior, three-dot menu, settings, ROM import/reimport/remove flow, diagnostics export, and lifecycle handling work as SnapPad. All required Pokémon Snap controls are usable in gameplay.
- **D8. Stability and persistence.** Background/foreground, interruption, renderer rebuild, controller connect/disconnect, app termination, repeated course transitions, FlashRAM writes, and a 60-minute soak complete without stuck input, save corruption, sustained audio underrun, unbounded memory growth, or orphan processes.
- **D9. Reproducibility.** Technical matrix rows 1–23 are green, the regression suite is green, and the full macOS and Simulator pipeline reproduces from a clean checkout using scripts and pinned dependencies alone.
- **D10. Public candidate.** The exact source revision and exact binary/IPA candidate pass physical-device hands-on testing, repository/package audits, third-party notices, and the rights gate in Section 12. A candidate is not public until Chris explicitly approves that exact artifact.

Explicit non-goals for the baseline build:

- App Store submission, TestFlight, notarization, commercial signing, automatic updates, or store compliance work.
- ROM revisions or regions other than the verified US ROM above.
- Widescreen camera changes, 60 fps patches, texture replacement, free-camera modes, cheats, randomizers, mod loading, or gameplay changes. These may be explored only after D1–D9 and must be default-off experiments.
- Network play or multiplayer work; Pokémon Snap is treated as a single-player P1 title.
- Game Boy Pak, printer, or Controller Pak emulation unless call-graph and hands-on evidence prove one is required for baseline progression. Their “not present” paths must still return safely without hangs or crashes.
- Treating rumble as a progression blocker. Rumble is a Preview target when supported by the runtime and Apple controller APIs, but lack of rumble alone does not invalidate the core port if it is clearly documented.

## 3. Why this is feasible — and what remains unproven

Validated by source audit on 26 Aug 2026, against Pokémon Snap repository revision `11ee0fec2143bdd636ee0e9c714a402fd8c7d9fe` and PaperPad revision `74b6e45830a06c7f274c5ac1ddd7c625bc13a557`:

- **The repository already supplies the required ROM-to-ELF path.** Its documented pipeline accepts the exact US ROM, extracts/disassembles it, rebuilds it with Ninja, and declares `build/pokemonsnap.elf` and `build/pokemonsnap.map` as outputs. This is the metadata boundary N64Recomp needs.
- **The N64Recomp front end has already crossed the first Pokémon Snap-specific hurdle.** A public N64Recomp issue comment records using this decomp project to produce the ELF, identify an entry point, write a TOML configuration, and generate C output. That is evidence of parse/generation feasibility, not evidence of a working executable.
- **The toolchain supports the game's broad architecture in principle.** N64Recomp supports statically linked and relocatable overlays. N64ModernRuntime exposes overlay registration/loading/unloading and FlashRAM support. RSPRecomp supports fixed RSP microcode; RT64 supplies the modern renderer.
- **The game's overlay behavior is unusually legible.** `include/sys/dma.h`, `src/sys/dma.c`, `splat.yaml`, the linker map, and named segment symbols expose ROM ranges, RAM ranges, BSS, cache invalidation, and the central overlay loader. The game is overlay-heavy, but the problem is enumerable rather than anonymous.
- **The save format is explicit.** The source uses a 128 KiB FlashRAM path (`0x20000`) and named FlashRAM operations. N64ModernRuntime has a matching FlashRAM save type.
- **PaperPad has already solved the Apple-specific substrate.** Its repository contains AOT-only Apple builds, RT64 Metal/iOS patches, touch controls, ROM import, controller slot handling, diagnostics, clean-exit work, dependency locks, clean-clone scripts, package audits, and physical-device evidence. Port this machinery rather than reconstructing it.

The following are **not** validated by this review and must be proven by execution:

- That the current generated Pokémon Snap C output compiles and links against the PaperPad-derived runtime without game-specific patches.
- That every overlay and reused RAM region is represented correctly, especially where sections overlap or where a load/decompression path is not a plain ROM-to-RAM DMA.
- That Pokémon Snap performs no runtime-generated or self-modified MIPS execution outside the declared overlay model.
- That its audio and graphics microcodes work correctly through the selected RSPRecomp/RT64/HLE path, with no unsupported RSP overlay.
- That RT64 reproduces the game's photo framebuffer, thumbnails, reticles, fog, depth, sprites, and scoring inputs correctly.
- That FlashRAM writes, accessory probes, course transitions, scoring, and all progression remain correct on Apple targets.
- That any source or binary release is authorized. The audited Pokémon Snap repository root exposes no general `LICENSE` file.

**Conclusion:** proceed. This is a credible port target and materially more ready than an arbitrary N64 ROM because the exact decomp/ELF path, symbols, overlay definitions, and an existing N64Recomp generation attempt all exist. It is **not** an immediate release candidate. Overlay correctness, RSP/audio behavior, photo-system correctness, full progression, physical Apple testing, and public-rights clearance are real gates.

This feasibility review was source-level. No user ROM was available in this review environment, so no ROM rebuild, recompilation, launch, gameplay, timing measurement, or package audit has been personally executed. The agent must not convert this decision to proceed into an acceptance claim.

## 4. Environment and workspace

You have free rein on a macOS Apple Silicon machine. Verify and install what is missing: Xcode 26.x and command-line tools, CMake, Ninja, `uv`, Python 3, Git, `jq`, `ripgrep`, GNU-compatible MIPS binutils as required by the decomp build, and any exact compiler tools required by the current repository. `xcodebuild`, `xcrun simctl`, Instruments, and both iPad/iPhone Simulators must work.

Use the existing decomp repository as the project root. Do not place port glue into the existing game `src/` tree unless a deliberate game patch requires it. Recommended layout:

```text
docs/                         This PRD, GOAL-LOOP.md, journal, status,
                              technical inventories, and local evidence index.
ref/                          Gitignored, read-only or pinned source inputs.
  paperpad/                   Full PaperPad clone; reference implementation.
  paper-mario-recut/          PaperPad-pinned runtime/vendor tree.
  mupen64plus-rsp-hle/        Only if the selected audio path needs it.
  SDL2/
  zstd/
  rom/                        The user's original ROM; never modified.
config/
  snappad-us.toml             N64Recomp configuration generated from verified data.
generated/                    Entirely gitignored.
  rom/                        Normalized working ROM copy and rebuild checks.
  aot/                        N64Recomp/RSPRecomp output.
  build/                      Native build output and caches.
port/                         SnapPad-owned integration code.
  apple/                      macOS/iOS shell adapted from PaperPad.
  runtime/                    Game registration, overlays, paths, hooks, stubs.
  patches/                    Recomp/runtime/RT64 patches with provenance.
scripts/                      Reproducible setup/build/test/audit entry points.
tests/                        Host-side regression tests and test-input helpers.
```

Hard workspace rules:

- Never modify, rename, truncate, or delete the user's original ROM. Work from a normalized ignored copy.
- Treat `ref/paperpad` as read-only. Do not “improve” PaperPad in place and do not commit from inside it.
- Pin every checkout. Disable push URLs on source-reference checkouts, following PaperPad's script pattern.
- Never commit or upload any ROM, extracted asset, generated AOT game code, rebuilt ROM, save, in-game photograph data, crash dump containing game memory, or private diagnostic log.
- `docs/artifacts/` is local/ignored by default. Select screenshots for a public repository only during the explicit release review.
- Never run `git clean -fdx`, destructive resets, or blanket deletion in this repository. The ignored ROM, `ref/`, generated output, and evidence are intentionally valuable.
- Do not overwrite unknown local modifications. Inspect `git status`; preserve or isolate them.
- Do not push any branch, tag, release, package, or generated artifact unless Chris has set up the destination and explicitly authorized that action.

## 5. Inputs and repositories

### 5.1 The ROM

Keep the original in `ref/rom/`. Before any build work:

1. Identify byte order and normalize an ignored working copy to big-endian `.z64`.
2. Record filename, byte order, byte length, SHA-1, and SHA-256 in `docs/JOURNAL.md`.
3. Require SHA-1 `edc7c49cc568c045fe48be0d18011c30f393cbaf`.
4. Copy/link the normalized ignored working input to the path the decomp expects (`pokemonsnap.z64`) without moving the original.
5. Run the repository's exact rebuild and verify the rebuilt ROM against `checksum.sha1` and the expected SHA-1.

If the supplied ROM does not match, stop G1 with a clear handoff. Do not generate a “close enough” ELF from a different revision and do not silently patch the checksum.

### 5.2 The current Pokémon Snap repository

The audit revision was `11ee0fec2143bdd636ee0e9c714a402fd8c7d9fe`. At session start, record the actual HEAD and branch. The documented baseline pipeline is:

```bash
uv sync
uv run configure.py --setup
uv run configure.py
ninja
```

Expected declared outputs are `build/pokemonsnap.z64`, `build/pokemonsnap.elf`, and `build/pokemonsnap.map`. Verify the actual paths; do not merely assume they exist because `decomp.yaml` names them.

Keep decomp work and port-integration work reviewable. A change needed only to make the original ROM match belongs in the decomp side. A change needed only by the native port belongs under `port/` or the recomp patch pipeline. Do not weaken the matching build to make the port easier.

### 5.3 The reference implementation: `ref/paperpad`

Pin the reference clone to `74b6e45830a06c7f274c5ac1ddd7c625bc13a557` first. Newer PaperPad commits may be evaluated later, one deliberate update at a time.

Before writing port code, read in order:

1. `README.md` — supported targets, controls, ROM setup, settings, diagnostics, and current release boundary.
2. `docs/ARCHITECTURE.md` — ROM-to-ELF-to-AOT boundary, runtime/RT64 integration, AOT-only Apple design, Apple shell, saves, and shutdown.
3. `docs/BUILDING.md` and `docs/DEPENDENCIES.md` — exact build sequence, dependency pins, patches, clean-clone behavior, and host-tool requirements.
4. `docs/TESTING.md` — evidence rules, end-to-end acceptance, one-Simulator rule, lifecycle, and physical-device distinctions.
5. `docs/STATUS.md`, `docs/KNOWN-ISSUES.md`, `docs/TECH-DEBT.md`, and `docs/HANDOFF.md` — solved failures and claims that remain deliberately bounded.
6. `docs/RELEASE_CHECKLIST.md`, `RIGHTS_AND_LICENSES.md`, and `docs/INSTALL_IPA.md` — source/package safety and exact-artifact release discipline.
7. `dependencies.lock.json` — the pinned source graph.
8. `scripts/` — especially `clone-sources.sh`, `verify-sources.sh`, `apply-patches.sh`, `prepare-rom.sh`, `build-decomp.sh`, `build-host-tools.sh`, `generate-game.sh`, `build-macos-app.sh`, `build-ios-simulator.sh`, `capture-crashes.sh`, `check-repo-safety.sh`, `audit-ios-package.sh`, and `package-unsigned-ipa.sh`.
9. `patches/` — N64Recomp, N64ModernRuntime, RT64, Metal lifetime/resource, no-dynamic-code, audio, VI-cadence, and clean-exit patches. Inspect applicability; do not blindly apply Paper Mario-specific patches.
10. `apple/app/`, `src/`, and `tests/` — shell, ROM setup, diagnostics, touch latch, controller slots, runtime context, game hooks, overlay registration, and regression style.

PaperPad is the proof of process, not proof that Pokémon Snap needs the same game-specific fixes. Port mechanisms and evidence discipline wholesale; port patches only after source inspection and an observed need.

### 5.4 Core toolchain and starting pins

Start from the PaperPad dependency graph because it is already proven on Apple targets. Create a new root `dependencies.lock.json` for SnapPad and record the resolved recursive revisions.

| Input | Role | Starting state |
|---|---|---|
| `ref/paperpad` | Apple reference implementation | `74b6e45830a06c7f274c5ac1ddd7c625bc13a557` |
| `github.com/SMCGames/Paper-Mario-ReCut` | Pinned vendor tree containing N64ModernRuntime, N64Recomp, and RT64 | `098be0a501eecd5bb894a47964061d05eeedc3a2` |
| Nested N64Recomp/RSPRecomp | MIPS and RSP static recompiler host tools | Resolve from ReCut's recursive submodules; record exact commits |
| Nested N64ModernRuntime | N64 OS/runtime, overlays, PI DMA, saves, input/audio integration | Resolve from ReCut's recursive submodules; record exact commit |
| Nested RT64 | Metal renderer and host integration | Resolve from ReCut's recursive submodules; record exact commit |
| `github.com/mupen64plus/mupen64plus-rsp-hle` | Diagnostic or documented HLE audio path, only if required | `8a7a472a7172eb2c8725b305eae26818ed7b51a2` |
| `github.com/libsdl-org/SDL` | Native host/input/window dependency where retained | `5d249570393f7a37e037abf22cd6012a4cc56a71` |
| `github.com/facebook/zstd` | RT64/vendor build input | `794ea1b0afca0f020f4e57b6732332231fb23c70` |

The current upstream N64Recomp and N64ModernRuntime may contain improvements beyond PaperPad's pins. Do not update reflexively. First produce a known-good baseline from the PaperPad-pinned graph. Moving any nested pin means rebasing the applicable PaperPad patches and rerunning the full matrix.

### 5.5 Pokémon Snap-specific source map

Read these before generating the first native build:

| Path | What it establishes |
|---|---|
| `decomp.yaml` | Expected ROM hash and declared ROM/ELF/map output paths |
| `splat.yaml` | Main and overlay section layout, ROM/RAM ranges, RSP binaries, and reused RAM groups |
| `include/sys/dma.h` | Overlay descriptor and ROM/VRAM/BSS fields |
| `src/sys/dma.c` | Central overlay/DMA/cache behavior and VPK0-related data paths |
| `src/sys/main.c` | Initial overlay loading and scene-manager entry |
| `src/sys/cont.c` | Controller and accessory detection/probe behavior |
| `src/more_funcs/5D500.c` | FlashRAM size and read/erase/write operations |
| `src/app_level/player.c` | Camera, zoom, shutter, item, pause, and course input behavior |
| `build/pokemonsnap.map` | Actual linked symbols and section boundaries from the verified build |
| `build/pokemonsnap.elf` | N64Recomp metadata input; ground truth for entry point and executable sections |

Use the verified ELF/map, not guessed addresses from a forum comment. Named symbols make every overlay failure, lookup fault, profile, and patch cheaper.

## 6. Phase 0 gate: reproducibility and public-rights state

Technical work may proceed privately once the state is recorded. Public work may not proceed until the release gate is cleared.

1. Create `docs/RIGHTS-STATUS.md` with the current state: **private technical work permitted by Chris; public redistribution not approved**.
2. Record that the audited Pokémon Snap repository root has no general `LICENSE` file. Check the current revision again; do not infer permission from repository visibility or decomp availability.
3. Choose and record the intended release topology, without publishing it yet:
   - maintainer-approved integration in this repository with an explicit license;
   - a separate SnapPad integration repository that treats the pinned decomp checkout as a local build input and copies no unlicensed source; or
   - private fork only.
4. Port PaperPad's source-clone safety pattern: exact pins, dirty-check refusal, recursive submodules, push URL disabled.
5. Port repository safety checks before generated output exists: ROM patterns, generated AOT paths, saves, logs, crash dumps, absolute user paths, signing data, and known asset directories must be ignored and rejected from commits.
6. Complete the exact ROM rebuild and ELF/map verification from Section 5.1.

G0/G1 can be complete while `RIGHTS-STATUS.md` remains `private-only`. That state blocks only G12/publication, not the private technical program.

## 7. Phase 1 gates: AOT generation, overlays, RSP, and saves

### 7.1 Entry point and N64Recomp configuration

Generate `config/snappad-us.toml` from verified data, following PaperPad's minimal configuration style:

- `elf_path` points to the verified `build/pokemonsnap.elf`.
- `rom_file_path` points to the ignored normalized ROM.
- `output_func_path` points under ignored `generated/aot/`.
- `entrypoint` is derived from the verified ELF/ROM boot path and recorded in `docs/OVERLAYS.md`; do not copy an unverified address.
- The generated include targets the selected `librecomp` headers.
- Every warning is captured. Suppress a warning only after interpreting and documenting it.

Generate output from a clean AOT directory, inventory the emitted section tables and unresolved warnings, then compile it with Clang on macOS. Generated C existing on disk is not G2; it must compile and link into the runtime.

### 7.2 Overlay manifest — the primary technical gate

Pokémon Snap repeatedly replaces code/data in shared RAM ranges. Build `docs/OVERLAYS.md` and, where practical, a generated machine-readable manifest. For every executable section record:

- logical name and source segment;
- ELF section/index and symbol prefix;
- ROM start/end and size;
- link-time VRAM start/end;
- runtime destination range;
- text/data/BSS boundaries;
- whether it belongs to a reused/exclusive RAM group;
- load call site and loader function;
- direct DMA versus decompression/other transform;
- expected predecessor/successor overlays;
- test scene that proves it executed.

At minimum inventory the resident/main path, `app_render`, `world`, course/level overlays, and menu/application overlays including Oak's Lab, camera/photo check, album/report/gallery, and end-level flows. Derive the final list from the verified ELF and `splat.yaml`; do not rely on this prose as a complete list.

Register the generated section tables using PaperPad's `src/register_overlays.cpp` pattern and N64ModernRuntime's overlay API. Then wire the game's central overlay transition correctly:

1. Identify the exact ROM and RAM span that will be replaced.
2. Call `unload_overlays` for the complete old executable destination span when required.
3. Perform/retain the game-visible ROM DMA and BSS/cache behavior.
4. Call `load_overlays` with the exact ROM, RAM, and size for the newly resident executable sections before any indirect call can target them.
5. Emit `overlay-load` / `overlay-unload` breadcrumbs with names, ROM/RAM ranges, sizes, and section indices.

N64ModernRuntime rejects partial unloads. If the game's transfer does not align to whole generated executable sections, fix the section/manifest boundary or implement a narrowly justified game-specific route; do not widen ranges until an assertion disappears.

Audit every VPK0 path separately. Do not assume that a compressed data path is executable, and do not assume that every executable load is a direct DMA. Any executable bytes produced by decompression or transformation need an explicit supported registration strategy.

Overlay acceptance evidence must include successful transitions into and out of every course and major menu overlay, plus a log proving no stale function mapping survived an overlapping load.

### 7.3 Dynamic-code and indirect-call audit

N64Recomp has no general interpreter safety net for omitted executable behavior. Before calling the overlay model complete:

- Search for stores into executable RAM ranges, deliberate instruction-cache invalidation, and jumps into RAM not represented by an ELF code section.
- Separate ordinary overlay cache invalidation from true runtime-generated/self-modified code.
- Record all indirect-call lookup failures with current overlay identity, target RAM address, source function, and expected section.
- Exercise idle/demo scripts, course transitions, photo review, gallery, and credits because unusual indirect calls often live outside first gameplay.
- Patch a specific function or call path only after naming the original behavior and writing a regression for it.

If true dynamic MIPS code exists outside a bounded, patchable path, leave G2 unmet and write the exact blocker. Do not hide it behind a no-op stub.

### 7.4 RSP and audio gate

Create `docs/RSP.md`. Inventory every RSP binary/task from the verified build. The source map includes an RSP boot path, an `aspMain` audio microcode, and F3DEX2/L3DEX2-family graphics microcodes; verify exact hashes and load behavior from the ROM/ELF.

Required process:

1. Confirm whether each microcode is fixed or overlaid at runtime. N64Recomp currently documents no RSP-overlay support.
2. Attempt the PaperPad-style recompiled audio RSP path first when the microcode is supported.
3. Use HLE audio only as a deliberate diagnostic or documented shipping decision, never as a silent fallback. Record which tasks use it and why.
4. Route graphics tasks through the selected RT64 path and capture unsupported-opcode/task evidence.
5. Verify music, ambient course audio, Pokémon sounds, UI sounds, photo shutter, transitions, and credits.
6. Track queue depth, underruns, pitch, and desynchronization with timing evidence.

A title screen with missing or incorrect audio does not pass G4/G5.

### 7.5 FlashRAM and accessories gate

Register Pokémon Snap as a **128 KiB FlashRAM** game. Create `docs/SAVE-AND-ACCESSORIES.md` and test:

- blank save initialization;
- profile/name creation;
- writes after course/photo review;
- relaunch and load;
- repeated writes and app termination;
- backup/recovery behavior;
- erase/new-game flow;
- no cross-talk between test saves;
- no write outside `0x20000` bytes.

Controller/accessory rules:

- Standard controller P1 input is required.
- The no-accessory path must be the default and must never hang on probes.
- Rumble may be implemented through Apple controller haptics/rumble when supported; log capability and failure cleanly.
- Controller Pak, Game Boy Pak, and printer paths remain absent unless later made explicit features. Stub only the physical-device absence, not game logic that depends on the result.

### 7.6 Phase 1 pass condition

Phase 1 is complete only when:

- the verified ELF generates AOT output;
- the AOT output and required RSP output compile and link;
- the complete executable-section manifest exists;
- resident code and the first required overlays register without unresolved lookups;
- save type and accessory behavior are explicitly configured;
- all warnings, patches, and remaining risks are recorded.

## 8. Phase 2: macOS bring-up and complete-game path

Build the pipeline by porting PaperPad's script shape, not by accumulating one-off terminal history. The final names may be adapted, but provide single-purpose scripts equivalent to:

```text
scripts/check-prerequisites.sh
scripts/clone-sources.sh
scripts/verify-sources.sh
scripts/apply-patches.sh
scripts/prepare-rom.sh
scripts/build-decomp.sh
scripts/build-host-tools.sh
scripts/generate-game.sh
scripts/build-macos-app.sh
scripts/build-ios-simulator.sh
scripts/capture-crashes.sh
scripts/check-repo-safety.sh
scripts/audit-ios-package.sh
scripts/package-unsigned-ipa.sh   # created but not authorized for release by this PRD
```

Bring-up ladder, each rung tested immediately and backed by a screenshot/log:

1. Native process starts, initializes the runtime, and creates a Metal surface.
2. ROM validation/first-run UI accepts only the correct ROM and stores only a private local copy.
3. Resident code reaches the title screen with stable rendering and audio.
4. Controller/keyboard input navigates the title and new-game/name-entry flow.
5. Oak's Lab loads and returns correctly.
6. Beach loads; the player camera moves and aims.
7. Z zoom works in its configured hold/toggle behavior; A takes a photograph while zoomed; A throws an apple when appropriate; B throws a Pester Ball when unlocked; Down-C activates the Poké Flute when unlocked; Start pauses; C-button behavior is preserved.
8. A full Beach run finishes and transitions to photo selection/review.
9. Oak recognizes the submitted subject and produces stable score components/total.
10. Progress writes to FlashRAM, the app exits cleanly, and relaunch restores it.

Only after rung 10 works should the app be described as “playable.” Package a normal macOS `.app` using the PaperPad app/runtime structure, renamed and stripped of Paper Mario assumptions.

Then complete a fresh-save golden path through:

- Beach
- Tunnel
- Volcano
- River
- Cave
- Valley
- Rainbow Cloud
- credits/post-game return

Record every unlock/progression transition. Maintain a separate ignored later-game save fixture for fast regressions, but do not use it as the only proof of progression. At least one fresh-save completion must be observed.

## 9. Phase 3: timing, rendering, photo correctness, and Apple shell

### 9.1 Native timing and performance

Do not set a performance target from memory. Establish the original US baseline first:

1. Instrument VI events, game update cadence, rendered-present cadence, and audio task cadence in a known-good reference run.
2. Record the expected cadence for title, lab, each course, photo capture, review, gallery, and credits in `docs/PERF.md`.
3. On macOS, measure worst-case frame interval and frame pacing, not just average fps. Include audio and overlay transitions.
4. Profile with Instruments and runtime counters. Change one variable at a time and re-measure.
5. Verify audio pitch and course scripting against elapsed game time, not merely visual smoothness.
6. Keep enhancements disabled. A 60 fps or widescreen experiment cannot become the stable path until the baseline matrix is green.

Required profile scenes include dense Pokémon/particle moments in each course, photo shutter/capture, end-of-course transitions, Oak's photo review, Gallery/Album, and credits.

### 9.2 Photo-system correctness — a dedicated gate

Pokémon Snap's product is the photo pipeline; it cannot be treated as incidental UI. Verify:

- reticle, zoom viewport, camera matrices, and input sensitivity;
- photo shutter timing and film count;
- rendered image capture/readback;
- subject detection and in-focus state;
- special-subject flags and multi-Pokémon cases;
- size, pose, technique, same-Pokémon, and total scoring;
- photo selection, report replacement, album/gallery storage, thumbnails, and reload;
- transitions between course render state and photo-review render state;
- no stale framebuffer, inverted image, missing depth/fog, or incorrect crop/aspect.

Create a deterministic local “golden photo route” using scripted input where possible. Record the resulting subjects and score components. Automated evidence can detect regressions; final acceptance still requires hands-on photo taking.

### 9.3 iPadOS/iOS Simulator core

Port the PaperPad Apple runtime and RT64 Metal patches; do not reinvent them. Preserve the AOT-only boundary: no JIT, TCC, downloaded code, or runtime-generated executable code.

- Build an iPad Simulator first and prove the first-play loop.
- Shut it down, then build/run an iPhone Simulator.
- Reuse PaperPad's Metal device/window/main-thread/resource/lifetime fixes, native-file-dialog guards, clean-exit work, and no-dynamic-code runtime patch where applicable.
- Treat Paper Mario-specific audio headroom, VI cadence, FlashRAM, or HLE patches as hypotheses. Inspect and reproduce the underlying need before porting them.
- Record Simulator performance but do not make device-tier claims from it.

Run only one Simulator and one game instance at a time; the operating procedure is in `docs/GOAL-LOOP.md`.

### 9.4 Porting the PaperPad shell

Port the PaperPad shell into `port/apple/` and `port/runtime/`, renaming PaperPad → SnapPad only after separating game-neutral code from Paper Mario-specific code.

**Touch controls:** start from PaperPad's complete N64 overlay so no original control is unavailable, then tune for Pokémon Snap:

- a large, precise analog camera/turn stick or drag region;
- a large **A/shutter** control, recognizing that A is context-sensitive and also throws an apple outside the photo action;
- a prominent **Z/zoom** control usable in both hold and toggle modes;
- **B** for Pester Ball;
- **Down-C** for Poké Flute;
- accessible remaining C buttons for the game's camera/turn behavior;
- **Start** for pause;
- all remaining N64 buttons available in layout-edit mode even if rarely used.

Retain PaperPad's move/edit mode, drag customization, independent size/opacity, safe-area handling, reset-to-default, separated phone/tablet defaults, tap-latch/edge correctness, and automatic hide when a physical controller takes P1. No touch region may remain logically held after a menu, alert, share sheet, interruption, controller handoff, or app backgrounding.

**Three-dot menu:** feature parity with the game-neutral PaperPad mechanisms:

- render resolution Auto and supported 1x–4x choices;
- original 4:3 default; Fill/widescreen-like modes clearly experimental unless proven correct;
- image filtering options only where the RT64 path supports them safely;
- audio volume;
- touch controls on/off, layout edit/reset, size, and opacity;
- Game Data: import, verify, reimport, remove, and show supported ROM identity;
- Saves: show location/status and expose only safe user actions;
- Share Diagnostic Log;
- Report a Problem;
- About, third-party notices, and rights wording;
- default-off experimental toggles with logged mode identity and restart semantics where required.

**Controller and lifecycle:** Pokémon Snap is P1-only, but keep PaperPad's robust ownership rules: stable P1 selection, physical-controller reclaim, touch auto-hide, held-input clearing, disconnect recovery, and no input leakage while native UI is open. Test background/foreground, audio interruption, renderer recreation, orientation/safe-area changes, memory warnings, and clean shutdown.

**Diagnostics:** port PaperPad's breadcrumb system early. Log boot phase, ROM validation, game identity/hash, display and renderer state, overlay load/unload, RSP task mode, controller ownership, input clear, lifecycle, save writes, photo-system milestones, memory warning, runtime warning/error, screenshot marker, and clean exit. Write to `Library/Application Support/SnapPad/Logs/runtime.log` (or the platform-equivalent container path) and export a privacy-bounded log that contains no ROM bytes, generated code, save contents, photographs, absolute private paths, or signing information.

## 10. Phase 4: test matrix

Adopt PaperPad's testing rules wholesale, especially: **compilation success is not gameplay success; run only one Simulator at a time; and do not convert configured or source-inspected behavior into an acceptance claim.** Capture dated evidence for every row: target, hardware/Simulator, OS, build configuration, root git revision, dependency-lock revision, ROM hash, commands, logs, screenshots/captures, result, and remaining defects. Use `xcrun simctl io <device> screenshot` for Simulator evidence. Rows marked hands-on require real interaction; scripted input does not satisfy them by itself.

| # | Row | Target | Pass condition |
|---|---|---|---|
| 1 | Repository safety and rights state | repo | `RIGHTS-STATUS.md` exists; private/public state is explicit; ROM/AOT/save/log patterns are ignored and rejected by safety checks |
| 2 | Exact ROM rebuild and ELF | clean checkout | Correct US ROM verified; `ninja` rebuild matches expected checksum; ELF/map exist; entry point and hashes recorded |
| 3 | AOT/RSP generation and overlay table | repo + macOS build | N64Recomp/RSPRecomp complete; generated code compiles; every executable section is inventoried; no unresolved lookup or partial-unload defect |
| 4 | Boot to title | macOS, iPad Sim, iPhone Sim | Title renders with audio and accepts input; evidence screenshot and clean runtime log |
| 5 | First-run, new game, and Oak's Lab | all three | Correct-ROM import/validation works; name/new-game flow and lab navigation complete |
| 6 | Beach first-play loop | macOS hands-on; iPad Sim hands-on | Course loads; camera/zoom/shutter work; course completes; photo review/scoring returns to lab |
| 7 | Tunnel | macOS hands-on | Full course completes; expected overlay transitions, Pokémon behavior, audio, and progression occur |
| 8 | Volcano | macOS hands-on | Full course completes with no render, timing, audio, or progression blocker |
| 9 | River | macOS hands-on | Full course completes with no render, timing, audio, or progression blocker |
| 10 | Cave | macOS hands-on | Full course completes with no render, timing, audio, or progression blocker |
| 11 | Valley | macOS hands-on | Full course completes with no render, timing, audio, or progression blocker |
| 12 | Rainbow Cloud and credits | macOS hands-on | Final course, end sequence, credits, and post-game return complete |
| 13 | Progression and item unlocks | macOS | Fresh-save route unlocks required courses/items; apple, Pester Ball, Poké Flute, Dash Engine, and pause/camera modes behave when available |
| 14 | Photo pipeline and scoring | macOS + iPad Sim | Golden photo route preserves capture, subject detection, score components, report/album/gallery, thumbnails, and reload |
| 15 | FlashRAM persistence | macOS + iPad Sim | Fresh save, repeated write, relaunch, erase/new game, backup/recovery, and termination tests pass without corruption |
| 16 | Audio continuity | macOS + iPad Sim | Music, ambience, Pokémon sounds, UI, shutter, transitions, and credits have correct pitch and no sustained underrun/desync |
| 17 | Timing, rendering, and performance | macOS | Baseline cadence recorded; worst-case pacing/profile captured in all required scenes; no material deviation or unbounded memory growth |
| 18 | Touch overlay | iPad Sim hands-on + iPhone Sim hands-on | Every required control works in course and menus; hold/toggle zoom, tap latch, layout edit/reset, safe areas, and no stuck inputs pass |
| 19 | Menu/settings/ROM management | iPad Sim + iPhone Sim | Every menu entry functions; settings persist; resolution/aspect/filter apply safely; import/reimport/remove handles correct and incorrect ROMs |
| 20 | Controller and lifecycle | iPad Sim + iPhone Sim | P1 ownership, touch auto-hide/show, connect/disconnect, input clearing, background/foreground, interruption, renderer return, and clean exit pass |
| 21 | Diagnostics and privacy | macOS + iPad Sim | Export contains required breadcrumbs and mode identity; excludes ROM, code, saves, photographs, private paths, and secrets |
| 22 | Regression suite and clean clone | fresh directory | Ported host tests and scripted smoke tests pass; the entire pipeline reproduces from scripts and pins with no undocumented manual step |
| 23 | Soak and repeated transitions | macOS + iPad Sim | At least 60 minutes including repeated course/lab/photo-review cycles; stable memory/audio/save/overlay state |
| 24 | Exact public candidate | physical iPad + iPhone + repo/package audit | Chris plays the exact candidate through first-play and a later-game fixture; source/package audits and Section 12 rights gate pass; candidate hash recorded |

Simulator success does not satisfy row 24. A public source release and a public binary/IPA release are separate decisions and may have different rights outcomes.

## 11. Evidence, journal, and reporting

Maintain in `docs/`:

- `JOURNAL.md`: append-only and dated. Every session records the lowest unmet goal, exact step, commands, result, evidence path, blocker analysis, and next step.
- `STATUS.md`: current goal, bring-up rung, matrix state, current known-good commands/artifact hashes, and open defects. Overwrite freely; keep current.
- `RIGHTS-STATUS.md`: private/public authorization state, repository license findings, dependency-license inventory status, release topology, and decisions needed.
- `OVERLAYS.md`: complete executable-section/overlay manifest, runtime load/unload mapping, observed sequences, unresolved lookups, and patches.
- `RSP.md`: microcode identities/hashes, selected execution path, HLE/recompiled decisions, task failures, and audio evidence.
- `SAVE-AND-ACCESSORIES.md`: FlashRAM behavior, save-path tests, accessory probes/stubs, rumble status, and corruption/recovery tests.
- `PERF.md`: reference cadence, every frame/present/audio measurement, profile setup, scene, before/after optimization numbers, memory/soak history, and known deviations.
- `RELEASE-READINESS.md`: exact candidate revision/hash, matrix summary, physical-device evidence, source/package audit results, third-party notices, and explicit go/no-go.
- `artifacts/`: local ignored screenshots, videos, profiles, logs, crash captures, and save hashes, organized by date. Never commit wholesale.

Every acceptance record must identify the target and what was actually observed. A source read proves only source intent. A configured save type proves only configuration. A build proves only compilation. A process proves only launch. A screenshot proves only that frame. A Simulator proves only Simulator behavior. A different artifact proves nothing about the release candidate.

Honesty rule: **if it was not run and observed, it is not done.** Do not convert configured or source-inspected behavior into gameplay, performance, persistence, physical-device, or release claims.

## 12. Public release, legal, provenance, and wording

This section is an engineering release gate, not legal advice.

### 12.1 Current blocker

At the audited revision, the Pokémon Snap repository root exposes no general `LICENSE` file. A public GitHub repository is not automatically permission to copy, modify, redistribute, or combine its source into a public derivative. Therefore:

- private local feasibility work may proceed under Chris's direction;
- no public SnapPad source merge, fork release, binary, IPA, generated output, or tag is authorized by this PRD;
- obtain explicit maintainer/license clarity or choose a release topology that does not redistribute unlicensed upstream source;
- verify every dependency's exact license and notice requirements separately.

### 12.2 Release topology decision

Before public source publication, `RIGHTS-STATUS.md` must select one:

1. **Maintainer-approved in-repo integration.** Upstream maintainers approve the port work and establish explicit licensing for the relevant source.
2. **Separate integration repository.** SnapPad contains only original integration code, scripts, patches permitted by their licenses, and documentation; it clones the exact Pokémon Snap decomp as an ignored local build input. Do not assume this alone resolves every derivative-work question.
3. **Private-only project.** No public source or binary distribution.

The safest technical topology is usually a separate integration repository, but permission/legal review—not convenience—decides.

### 12.3 Source and package boundary

Port PaperPad's safety checks and strengthen them for Pokémon Snap. Public source/package audits must find no:

- ROM or rebuilt ROM;
- extracted Nintendo assets, audio, models, textures, strings, or photo data;
- generated N64Recomp/RSPRecomp C/AOT source;
- saves, crash memory, private logs, or test fixtures containing game data;
- signing identities, provisioning profiles, credentials, tokens, absolute private paths, or machine-specific secrets;
- accidental contents of `ref/` or `generated/`.

A ROM-free native binary may still contain statically translated game logic. **ROM-free is not automatically distribution clearance.** Treat source publication and binary/IPA publication as separate rights decisions.

### 12.4 Approved description wording

Use this substance in README/About/release notes once publication is authorized:

> SnapPad is an unofficial native Apple port built through ahead-of-time static recompilation of a user-supplied Pokémon Snap (US) Nintendo 64 ROM. It uses N64Recomp, N64ModernRuntime, and RT64 for the recompilation, runtime, and rendering stack. Users must supply their own legally obtained supported ROM. SnapPad is not affiliated with, endorsed by, or sponsored by Nintendo, The Pokémon Company, or their partners.

Do not describe the project as official. Do not say “emulator-free.” Do not imply that decompilation, ROM ownership, or a ROM-free package automatically grants redistribution rights.

### 12.5 Public-candidate gate

A public candidate requires all of the following in `RELEASE-READINESS.md`:

- D1–D9 and matrix rows 1–23 green;
- exact source revision and artifact hashes;
- Chris's physical iPad/iPhone acceptance of that exact artifact;
- repository and package audits green;
- third-party notices complete;
- explicit source-release and binary-release rights decisions;
- no unresolved severity-1 progression, save, crash, privacy, or package issue;
- Chris's explicit final authorization.

## 13. Risk register

| Risk | Standing | Response |
|---|---|---|
| No general license at Pokémon Snap repo root | Confirmed at audited revision; public-release blocker | Record private-only state now; obtain maintainer/license clarity or separate integration topology before publication |
| Extensive overlapping overlays | Confirmed; main technical risk | Generate complete manifest; explicit full-range unload/load hooks; log every transition; course/menu matrix coverage |
| Partial overlay unload mismatch | Runtime asserts on partial unload; game transfer boundaries unproven | Align generated sections and runtime ranges from ELF/map; never silence the assertion by arbitrary widening |
| VPK0/decompression paths | Present in DMA/data code; executable relevance unproven | Classify each path; build an explicit route for any executable transformed load; do not conflate assets with code |
| Runtime-generated/self-modified MIPS | Unverified | Executable-range write/cache/jump audit; named lookup logging; bounded patches only; no silent stubs |
| RSP microcode compatibility | Fixed audio/graphics families visible; actual runtime path unproven | Hash/inventory tasks; recompile supported audio; documented HLE diagnostic path; reject unsupported RSP overlay |
| Photo framebuffer/readback | Core game mechanic; RT64 correctness unproven | Dedicated photo matrix, deterministic score route, thumbnails/gallery tests, visual/reference captures |
| FlashRAM persistence | Source indicates 128 KiB; Apple lifecycle unproven | Explicit save type; repeated/termination/erase/recovery tests; local backups; no out-of-range writes |
| Accessory probes | Generic code detects rumble/Controller Pak/GB Pak/printer | Stable “not present” path; implement rumble where practical; keep optional devices out of baseline without hangs |
| Native timing/cadence | Exact target unmeasured | Instrument reference VI/update/present/audio cadence; preserve baseline before enhancements |
| PaperPad patch overreach | Apple substrate proven, game-specific patches may not transfer | Inspect each patch; port mechanisms first; reproduce symptom before applying game-specific fix |
| Toolchain drift | Upstreams active; PaperPad patches tied to pins | Start at PaperPad pins; new dependency lock; one deliberate upgrade at a time; full matrix after changes |
| Decomp WIP churn/build fragility | Repository is active and setup can change | Record root revision; exact rebuild/clean-clone gates; keep port changes isolated and scripts deterministic |
| Full-game regression cost | Fresh completion is long | One observed fresh-save golden path plus ignored later-game fixtures and scripted smoke routes; fixtures never replace full proof |
| Simulator/device gap | Simulator cannot prove heat, memory pressure, touch feel, audio route, or sustained device performance | Chris tests exact physical candidate; no physical claim before evidence |
| ROM-free package misconception | Binary may still contain translated game logic | Separate technical package audit from explicit rights decision; never auto-publish |
