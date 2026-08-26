# SnapPad goal-based loop

Operating loop for the autonomous build of SnapPad. The requirements live in `docs/PRD.md`; this document is how you run. Written 26 Aug 2026.

## The goal stack

Work the lowest unmet goal. A goal is met only when its evidence exists in `docs/` per PRD Section 11. Never work a higher goal while a lower one is broken; a regression reopens the lowest affected goal.

- **G0. Environment and state ready.** Toolchain verified; current git state recorded; `ref/paperpad` pinned/read; source checkouts pinned with push disabled; `RIGHTS-STATUS.md` says `private-only` or a stronger explicitly approved state; safety ignores/checks exist.
- **G1. Exact ROM rebuild and ELF.** Original ROM preserved; normalized working ROM matches SHA-1 `edc7c49cc568c045fe48be0d18011c30f393cbaf`; clean decomp pipeline produces a checksum-matching ROM, `build/pokemonsnap.elf`, and `build/pokemonsnap.map`; entry point and hashes recorded.
- **G2. Executable model proven.** Complete overlay/section manifest, dynamic-code audit, RSP inventory, FlashRAM registration, and accessory policy exist. N64Recomp/RSPRecomp generation completes with every warning interpreted.
- **G3. Native module compiles and links.** Generated AOT and SnapPad runtime glue compile into a macOS app with registered resident code/overlays and no unresolved native link failure.
- **G4. macOS boots to title.** Metal renders; audio runs; title accepts input; runtime/overlay/RSP breadcrumbs are clean.
- **G5. macOS first-play loop.** New game → Oak's Lab → Beach → take photos → course finish → Oak review/score → FlashRAM write → clean exit/relaunch/load. This is the minimum technical feasibility proof. (PRD D3)
- **G6. Complete macOS progression.** Fresh-save golden path completes all courses through Rainbow Cloud and credits, with expected unlocks, photo/report/album/gallery behavior, and no progression blocker. (PRD D4)
- **G7. Timing, photo correctness, and stability.** Original cadence documented; golden photo route stable; required performance profiles, audio checks, save tests, repeated transitions, and 60-minute soak pass. (PRD D5, D8)
- **G8. Simulator core boots.** iPad Simulator first, then iPhone Simulator, each reaches the first-play loop with the same AOT core and one Simulator running at a time. (PRD D6)
- **G9. PaperPad shell ported.** Snap-specific touch controls, three-dot menu, ROM management, settings, controller ownership, lifecycle, diagnostics, and privacy-bounded export work on iPad/iPhone Simulator. (PRD D7)
- **G10. Technical matrix green.** PRD matrix rows 1–23 pass with evidence; regression suite and clean-clone pipeline are green. (PRD D9)
- **G11. Physical candidate accepted.** Chris tests the exact candidate on physical iPad and iPhone; artifact hashes and hands-on evidence are recorded. This goal cannot be inferred from Simulator results.
- **G12. Public release authorized.** Repository/dependency rights, source boundary, binary boundary, notices, source/package audits, and Chris's explicit final approval are recorded. Only then may a public source release or binary/IPA release occur. (PRD D10)

G5 is the first hard feasibility gate. G6 and G10 are the technical release bar. G11 and G12 are mandatory for a public binary. There is no fallback to a title-screen demo, Beach-only release, unverified enhanced-framerate build, or “ROM-free therefore safe” release.

`RIGHTS-STATUS.md = private-only` does not block G1–G10. It blocks publication and G12.

## The loop

Repeat until the current authorized terminal goal is met:

1. **Pick** the lowest unmet goal. Choose the smallest concrete step that could advance it.
2. **Check state before acting.** Read `docs/STATUS.md`, the last `JOURNAL.md` entry, the relevant technical inventory, `git status`, running processes, booted Simulators, input hashes, dependency pins, and existing build caches. Do not rebuild or regenerate what a verified cache already holds.
3. **Execute** one bounded step.
4. **Test immediately.** Run the relevant check the moment the step completes. Compilation success is not gameplay success; a PID is not a booted game; a title is not a completed course; a completed course is not a saved/reloaded game.
5. **Capture evidence.** Put the screenshot, log excerpt, profile, hash, or capture under the local dated artifacts path. Append one dated journal entry: goal, hypothesis, step, command, result, evidence path, interpretation, next step.
6. **Update** `docs/STATUS.md` and the relevant inventory (`OVERLAYS.md`, `RSP.md`, `SAVE-AND-ACCESSORIES.md`, `PERF.md`, or `RIGHTS-STATUS.md`) if state changed.
7. **Continue.** If the step failed, enter the unblocking ladder before retrying.

## Process hygiene — hard rules

- **One Simulator at a time.** Before booting a Simulator, run `xcrun simctl list devices booted`; shut down every booted device, then boot only the intended iPad or iPhone. This is not optional.
- **One game instance at a time.** Before launching on any target, kill every previous SnapPad process, Simulator app instance, runtime process, and stray test harness. Multiple instances corrupt save/config evidence and create false renderer/input bugs.
- **Kill before relaunch, always.** Never layer a new run on a hung, crashed, or half-terminated run.
- **One variable at a time.** During debugging, overlay work, RSP/audio work, timing work, and optimization, change one thing, re-run the same evidence-producing test, and journal the result.
- **Clean up after crashes.** Check for a booted Simulator, orphan processes, locked save/config files, stale Metal capture, and partial logs before the next run.
- **Never touch the original inputs.** The original ROM and `ref/paperpad` are read-only. Work from ignored copies/checkouts. Hash spot-check when state is uncertain.
- **Never leak game data.** ROMs, rebuilt ROMs, extracted assets, generated AOT, saves, photographs, crash memory, and private logs never enter a commit, issue, upload, or public artifact.
- **No destructive cleanup.** Never run `git clean -fdx`, blanket `rm -rf` against the project root, destructive resets, or commands that can erase ignored inputs/evidence. Inspect paths first.
- **Respect unknown work.** Do not overwrite or reset local modifications you did not create. Isolate changes or write a handoff.
- **Pin before patching.** Verify the exact dependency revision before applying a PaperPad patch. A patch applying with fuzz is not proof it is correct.
- **No silent game-specific carryover.** Paper Mario-specific audio, VI, FlashRAM, UI, or gameplay patches are hypotheses until Pokémon Snap reproduces the need.
- **No silent stubs.** A stub is permitted only for an optional external device or a named, bounded path whose original result is understood. Never stub progression, scoring, save, overlay, RSP, or photo behavior merely to advance a screen.
- **No interpreter-fiction.** N64Recomp does not provide a general interpreter fallback for missing game functions. An unresolved executable path must be mapped or patched explicitly.
- **Timebox repetition.** The same command failing the same way twice is a blocker. Stop repeating it and enter the unblocking ladder. Never run an unchanged third attempt.
- **No publication by momentum.** A technically green build remains private until G12. Do not push releases, tags, packages, screenshots, or generated files without explicit authorization.

## Overlay discipline — hard rules

- Every indirect-call failure is an overlay/metadata incident until disproven. Record target address, source function, current overlays, and last load/unload events.
- Every executable load must map to a named manifest entry. “It seems like data” is not enough when the destination can execute.
- Unload complete generated sections. N64ModernRuntime's partial-unload assertion is a boundary error to understand, not an assertion to remove.
- Log and test overlay transitions, not just destinations. A course that works once may still leave stale mappings that break the next course or photo review.
- Never mark a course row green without its expected overlay sequence and return transition appearing in evidence.
- A VPK0/decompression path is classified by what it produces. Do not load it as executable unless the verified ELF/loader behavior proves it is executable.

## Unblocking ladder

When blocked, escalate through these in order. Journal each rung used.

1. **Read the actual error and full context.** Use `runtime.log`, unified logs, crash report, full build output, overlay breadcrumbs, RSP task log, save log, and the first causal error—not the final cascade line.
2. **Check the current project state.** Confirm ROM hash, root revision, dependency pins, generated config, cached AOT identity, active save, current overlay manifest, and whether the failure is reproducible from the last known-good command.
3. **Check PaperPad.** Read the exact reference script, patch, Apple shell code, test, and relevant `KNOWN-ISSUES.md` / `TECH-DEBT.md` / `TESTING.md` / `HANDOFF.md`. Reuse its mechanism only after identifying what is game-neutral.
4. **Check Pokémon Snap source and linked metadata.** Use `build/pokemonsnap.map`, ELF sections, `splat.yaml`, `include/sys/dma.h`, `src/sys/dma.c`, controller/save source, and named game functions to turn addresses into behavior.
5. **Check the toolchain source.** Read N64Recomp generation/analysis, generated section tables, N64ModernRuntime overlay/PI/save code, RSPRecomp, RT64, and the exact PaperPad patches at the pinned revisions.
6. **Research a specific question.** Search primary sources: N64Recomp/N64ModernRuntime/RT64 issues and source history, established recomp projects, decomp project discussions, and relevant libultra/microcode documentation. Research must answer a named blocker, then return to an experiment.
7. **Reduce the problem.** Examples: resident boot before the first dynamic overlay; one overlay transition with verbose mapping; direct DMA versus decompression; recompiled audio RSP versus documented HLE diagnostic mode; no-accessory path; one course; one deterministic photo; macOS before Simulator; stable renderer settings before experimental settings.
8. **Route around narrowly.** Replace or patch one named miscompiled function, overlay transition, libultra wrapper, or optional-device probe. Preserve original semantics, add a regression, and keep the stable path explicit. Do not replace an entire subsystem with no-ops.
9. **Park and pivot.** If a blocker survives the ladder for a working session, write a full reproducible defect and take the largest step on the same or later workstream that does not falsify the lowest goal—for example, shell extraction while waiting on an RSP investigation. Do not mark the blocked goal met.
10. **Stop and hand off only for a real decision/blocker.** Valid stop conditions: unusable/wrong ROM; exact decomp cannot reproduce and upstream state is insufficient; required upstream source is unavailable; true dynamic MIPS or RSP-overlay behavior has no bounded supported route; continuing would destroy/leak protected inputs; physical-device action is required; or a public rights/release decision is required. Ordinary crashes, compile errors, rendering defects, audio defects, save defects, and overlay mistakes have an unblocking path.

## Testing rhythm

- **Per change:** run the smallest build/boot/gameplay/regression check relevant to what changed.
- **Per overlay change:** exercise the load, use, unload/replacement, and return transition; inspect the mapping log for stale or duplicate functions.
- **Per RSP/audio change:** run a scene with music, ambience, UI sound, Pokémon sound, shutter, and transition; inspect task mode and underrun counters.
- **Per save change:** work on a disposable local save; hash/backup before and after; relaunch and verify game-visible state. Never commit the fixture.
- **Per goal claim:** complete the exact evidence required by PRD Section 11 before changing `STATUS.md` to met.
- **Per session:** run the host regression suite plus a boot/end-to-end smoke on the highest known-good target. End the journal with the exact known-good command, revision, artifact, save state, and next lowest goal.
- **Per candidate:** run the entire applicable matrix against the exact artifact; do not mix evidence from earlier builds.
- **Input automation:** port PaperPad's controller/touch state plumbing and add a SnapPad-only test-input path for repeatable menu/course/photo routes. Use `xcrun simctl io ... screenshot` for Simulator evidence. Rows marked hands-on remain hands-on.
- **Honesty rule:** do not convert configured or source-inspected behavior into an acceptance claim. If it was not run and observed, it is not done. Performance numbers only come from recorded measurements.

## Using the PaperPad machinery — not just its appearance

- **Dependency control:** port `dependencies.lock.json`, dirty-check refusal, recursive submodule setup, revision verification, and disabled push URLs. Produce a SnapPad-specific lock, not an informal list in the journal.
- **Scripts:** port the shape of `check-prerequisites.sh`, `clone-sources.sh`, `verify-sources.sh`, `apply-patches.sh`, `prepare-rom.sh`, `build-decomp.sh`, `build-host-tools.sh`, `generate-game.sh`, `build-macos-app.sh`, `build-ios-simulator.sh`, `capture-crashes.sh`, `check-repo-safety.sh`, `audit-ios-package.sh`, and `package-unsigned-ipa.sh` rather than inventing manual-only procedures.
- **AOT boundary:** preserve PaperPad's local ROM → exact decomp ELF → ignored N64Recomp/RSPRecomp output → ROM-free source tree boundary. No runtime-generated executable code on Apple targets.
- **Overlay registration:** use PaperPad's generated `recomp_overlays.inl` registration pattern, expanded for Pokémon Snap's dynamic load/unload behavior.
- **Apple shell:** extract game-neutral ROM setup, diagnostics, touch latch, controller ownership, paths, settings, lifecycle, Metal surface, and native UI behavior before renaming.
- **Logging:** wire breadcrumbs by G4, not after the port is already unstable. Overlay identity, RSP mode, save writes, and photo milestones are first-class diagnostics.
- **Experimental framework:** every risky cadence, renderer, HLE, scheduling, aspect, or enhancement experiment is default-off, carries a logged identity, and never silently replaces the stable baseline.
- **Release safety:** keep repository/package audits executable throughout development. Passing them once at the end is insufficient if the build graph changes.

## Session start checklist

1. Read `docs/STATUS.md`, the last `JOURNAL.md` entry, and the relevant inventory for the lowest goal.
2. Run `git status`; preserve unknown work. Record the root revision.
3. Run `xcrun simctl list devices booted`; shut down strays. Kill stray SnapPad/runtime/test processes.
4. Confirm the original ROM hash when relevant and verify the normalized working copy has not changed.
5. Verify `ref/paperpad` and toolchain revisions against the SnapPad dependency lock; check patches are applied to the intended commits.
6. Confirm the active save/test fixture and back it up if the session can write it.
7. State the session goal and smallest next step in `JOURNAL.md`.
8. Enter the loop.

## Session end checklist

1. Kill the game and shut down any Simulator.
2. Run the regression suite and highest known-good smoke test, or state exactly why one cannot run.
3. Record artifact/build identity, evidence paths, active save state, open processes (none expected), and remaining defect.
4. Update `STATUS.md` and any changed technical inventory.
5. Run repository safety checks before any commit.
6. Leave one unambiguous next step for the lowest unmet goal.
