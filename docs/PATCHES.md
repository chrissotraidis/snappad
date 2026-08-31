# SnapPad patch policy and inventory

Starting reference: PaperPad `74b6e45830a06c7f274c5ac1ddd7c625bc13a557` against Paper-Mario-ReCut `098be0a501eecd5bb894a47964061d05eeedc3a2`.

## Carried now

The maintained patches under `port/patches/` are game-neutral mechanisms required for Apple builds or the AOT-only boundary:

- N64Recomp/fmt compiler compatibility;
- SDL2 iOS controller press routing, so gamepad Select/A input is consumed by
  the controller profile without also becoming keyboard Return/Start;
- N64ModernRuntime no-dynamic-code Apple profile and bounded clean process exit;
- N64ModernRuntime's game-neutral FlashRAM full-chip-clear boundary fix
  (`[0, 0x20000)` is a valid 128 KiB range);
- RT64 external host-tool/zstd/SDL inputs;
- UIKit window and native-file-dialog guards;
- Metal device, main-thread, shader, render-target, resource-limit, lifetime, drawable, descriptor, and clear-state fixes;
- final-composite Fill Screen plumbing, retained as an explicit presentation
  setting. SnapPad also exposes RT64's separate expanded projection as a
  default-off experimental mode rather than mislabeling the crop as widescreen.

Every patch is applied only at its exact dependency pin. `scripts/apply-patches.sh`
requires a clean apply or an exact reverse-check proving it is already present;
fuzz is not accepted.

PaperPad's Fill Screen patch already carries the `rt64_present_queue.cpp` worker-lifetime hunks. SnapPad's copy of `metal-worker-lifetime.patch` removes only that duplicated file section so a clean source pin receives each change exactly once; all other worker-lifetime hunks remain byte-for-byte from PaperPad.

## Explicitly not carried without Pokémon Snap evidence

- Paper Mario audio headroom;
- Paper Mario/recompiled audio-RSP preference and synchronous audio scheduling changes;
- HLE NAUDIO behavior;
- Paper Mario VI/present cadence changes;
- Paper Mario FlashRAM page-wrap behavior;
- any Paper Mario gameplay, projection, save-fixture, or scene hook.

These remain hypotheses. A Pokémon Snap symptom, source explanation, bounded experiment, and regression evidence are required before adding one.
