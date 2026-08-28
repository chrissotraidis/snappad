# Pokémon Snap executable sections and overlays

Status: provisional source inventory generated; G2 remains unmet until the
verified G1 ELF/map supplies exact executable bounds and every load/unload path
is exercised at runtime.

`scripts/inventory-source-layout.sh` records the pinned decomp declarations in
ignored `generated/inventory/source-layout.json`. The current source declares
54 top-level `code` segments and 30 `Overlay` table entries used by
`dmaLoadOverlay`.

The runtime behavior is explicit in the decomp: an `Overlay` carries ROM, text,
data, and BSS bounds; `dmaLoadOverlay` invalidates caches, DMAs the ROM range to
its VRAM address, and clears BSS. The scene manager loads these families:

- seven course code overlays: beach, tunnel, cave, river, volcano, valley, and
  rainbow;
- matching mutually exclusive course asset overlays plus extra model/texture
  ranges;
- shared `world`, `app_level`, and `window` overlays;
- camera check, Oak's lab, album, report, photo check, gallery, credits, main
  menu, and new-game overlays;
- compressed VPK regions for main-menu, intro, and an unknown late segment.

Several segments deliberately reuse the same VRAM windows—for example camera
check, photo check, album, report, gallery, and the unknown end-level segment
all begin at `0x801DC8C0`. AOT generation therefore cannot treat a VRAM address
as globally identifying one function. The final G2 implementation must preserve
ROM-to-VRAM overlay identity and validate scene transitions, not merely compile
all symbols.

## Dynamic-code audit

The source-level audit found one real runtime-generated execution path. In
`src/app_level/504770.c`, `func_80364360_504770` decompresses
`unk_segment_AA18E0_vpk0` to `0x80200000`, writes the earlier SP IMEM/DMEM
integrity results beside it, and calls `0x80200000` as MIPS code. The payload's
only game-visible result in that function is to set `PFID_ILLEGAL_COPY` when
its result byte is nonzero. N64Recomp has no interpreter fallback for this
call, and Apple targets must not generate executable code at runtime.

SnapPad therefore injects one named entry hook for
`func_80364360_504770`. The native hook does not silently succeed: it preserves
the observable failure contract by setting `PFID_ILLEGAL_COPY` through the
original recompiled `setPlayerFlag` whenever either source SP integrity byte is
false. The two byte addresses are derived from the verified ELF into generated
metadata, and the host regression covers healthy, IMEM-failed, DMEM-failed,
and both-failed states. Once G1 is available, the exact decompressed payload
must still be compared before this route can be accepted as complete G2
evidence. `scripts/audit-dynamic-code.py` now makes that review fail-closed: it
derives the VPK0 ROM bounds from `splat.yaml`, verifies the normalized ROM
against G1 evidence, decompresses through the pinned decomp codec, disassembles
every big-endian word at its real `0x80200000` load address, and records the
payload hash plus mnemonic inventory in ignored
`generated/evidence/G2-dynamic-code.json`. The evidence deliberately says
`equivalenceReview: pending` and `gateComplete: false`; extraction is not a
claim that the native hook is equivalent.

The other two VPK0 call sites are data:

- `main_menu_vpk0` supplies sprites, textures, model/texture animations, and
  related structures to the separately loaded `main_menu` code overlay.
- `intro_code_vpk0` supplies sprite content to the separately loaded
  `intro_code` overlay; the historical segment name does not make it code.

Only `dmaLoadOverlay` calls `osInvalICache` in the current C source. That is
positive evidence that ordinary executable replacement is centralized, but
not runtime acceptance: unmatched functions and the verified ELF/map still
need inspection, and indirect lookup breadcrumbs must remain enabled through
all scene transitions.
