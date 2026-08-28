# Pokémon Snap RSP inventory

Status: exact inventory and generated audio path verified through macOS G4.
The supported ROM/rebuild supplies the recorded byte identities and RSPRecomp
configuration; a native title run produced non-zero samples with no conversion
or queue errors.

The pinned decomp declares four contiguous RSP text blobs in the main segment:

| Name | ROM start | Source-declared size | Intended role |
| --- | ---: | ---: | --- |
| `rsp/rspboot` | `0x3E4B0` | `0xD0` | RSP boot loader |
| `rsp/aspMain` | `0x3E580` | `0xE20` | audio microcode |
| `rsp/gspF3DEX2H.NoN.fifo` | `0x3F3A0` | `0x1390` | graphics microcode |
| `rsp/gspL3DEX2H.fifo` | `0x40730` | `0x1190` | line/graphics microcode |

`thread5_main` separately copies the RSP boot payload from cartridge physical
offset `0xB70` into `gRspBootCode`, then checks SP IMEM/DMEM before starting the
audio, controller, and scene threads. The final RSP manifest must hash the exact
verified byte ranges, map task selectors, and record whether each task uses
RSPRecomp, RT64 graphics handling, or an explicit diagnostic fallback. No HLE
audio fallback is selected silently.

## Fail-closed audio generation

`scripts/generate-rsp-config.sh` runs in the decomp's locked Python
environment after G1 and derives the RSPRecomp configuration from current
evidence:

- text offset and size come from `rsp-verified.json` and must remain
  `0x3E580 + 0xE20`;
- the task text address is `0x04001080`, and generation additionally requires
  the exact IPL3-derived boot payload copied by `thread5_main` to contain the
  matching RSP I-type load-address immediate;
- the `rsp/aspMain` data range is derived from `splat.yaml` rather than copied
  from Paper Mario;
- the handler-table DMEM offset is derived from the unique `lh target,...; jr
  target` pair in the exact microcode (`0x10` for Pokémon Snap); its 16
  big-endian handler PCs are normalized into the RSP IMEM window, deduplicated,
  alignment-checked, and rejected if outside the audio text range; and
- no `unsupported_instructions` early-return bypass is generated.

RSPRecomp writes ignored `generated/aot/rsp/aspMain.cpp`. Both its log and the
N64Recomp log then pass through `scripts/audit-generation-logs.py`. Any warning,
error, failed/unhandled/unsupported/unknown diagnostic stops G2 unless one
exact regular expression and a source-backed rationale are added to the
tracked allowlist. The accepted evidence contains three source-rationalized
diagnostic classes, 115 interpreted occurrences, and zero unresolved entries.

The native runtime now prefers a registered, verified RSPRecomp audio function
before Paper Mario's generic ParaLLEl/HLE fallbacks. The macOS title run logged
`first audio task routed to verified aspMain`, non-zero sample peaks, bounded
queue depth, and zero conversion/queue errors. This proves the opening/title
audio path only. Ambience, Pokémon cries, UI sounds, shutter, transitions,
pitch, extended underrun behavior, and device output remain G5/G7 evidence.
