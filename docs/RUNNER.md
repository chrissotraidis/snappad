# Native runner boundary

Status: the ROM-free arm64 macOS runner/runtime link probe passes. The private
production `SnapPad.app` target is staged but cannot link until G1/G2 supply
verified game CPU, overlay, metadata, and audio-RSP sources.

## PaperPad-derived mechanisms retained

`port/runtime/snappad_runner.cpp` is an executable derivation of the pinned
PaperPad runner. `scripts/audit-paperpad-runner-derivation.py` reconstructs it
from that exact reference and rejects drift. Retained mechanisms include:

- SDL2 window, event, keyboard, controller, and audio-stream plumbing;
- controller-slot reconciliation and short-tap latching;
- shared touch/controller input merging and bounded input breadcrumbs;
- private Application Support paths and native macOS ROM selection;
- ROM validation/storage through N64ModernRuntime;
- Apple Metal API selection, clean shutdown, and effective-render diagnostics;
- runtime callback assembly for RSP, renderer, audio, input, graphics, events,
  errors, and guest-thread names.

## Game-specific behavior removed or replaced

- Paper Mario ROM hash, game ID, internal name, and entrypoint are replaced by
  evidence-generated Pokémon Snap metadata.
- Paper Mario scene addresses, Goompa diagnostics, game-loop hook, built-in
  texture-pack seam, and `PSR_AUTOBOOT` behavior are absent.
- Rumble Pak reporting is replaced by the audited Pokémon Snap policy: one
  controller on port 1 with no pak; ports 2–4 absent.
- The audio callback names the generated Pokémon Snap `aspMain` function.
- Forced F3DEX branching, forced texture-LOD scaling, triple buffering, and
  PaperPad idle-work overrides are absent from the renderer baseline.
- Original game-space projection and original VI-rate presentation are the
  default. Fill Screen is an explicit final-presentation crop. Wide
  (Experimental) separately enables RT64's expanded projection; actual
  photo/reticle/timing correctness in that default-off mode remains a
  runtime gate.

## ROM-free link probe

`snappad_native_link_probe` uses two clearly scoped fixture symbols: an empty
recompiled entrypoint and an unsupported audio-RSP function. It is built only
to force the real host linker across the complete ROM-free dependency graph.
It is never launched, bundled, or linked into the production target. The probe
exposed one missing runtime ABI, `recomp_translate_address`; SnapPad now owns a
bounded RDRAM/TLB implementation with tests for cached/uncached aliases,
sign-extended addresses, mapping, unmapping, and TLB index masking.

## Production link contract

`scripts/build-macos-app.sh` requires real metadata, N64Recomp lookup/output,
and RSPRecomp `aspMain`. Before compiling it also verifies schema-2
`G2-generation.json`, which binds accepted diagnostics to hashes of G1, both
generation configs, native metadata, dynamic-code evidence, every generated
CPU source, and the generated audio RSP. A stale generated directory is not a
valid app input.

The resulting target is a private arm64 `SnapPad.app`. A successful future
link will satisfy only the compilation/link portion of G3; it will not imply
boot, rendering, audio, input, save, course, or progression acceptance.

## Bring-up breadcrumbs

The private diagnostics log records bounded milestones for the exact registered
core identity and entry point, generated section/overlay counts, first audio RSP
dispatch, renderer readiness, and the dynamic-code integrity failure path. These
markers are startup/first-occurrence events rather than per-frame tracing. They
are diagnostic prerequisites for G4, not evidence that any milestone ran until
they appear in a real-ROM boot log.
