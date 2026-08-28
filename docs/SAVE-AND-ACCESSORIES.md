# Save and accessory model

This document records the ROM-free source evidence, the conservative native
runtime policy, and the macOS evidence observed so far. Simulator, album,
recovery, erase, and physical-device acceptance remain open.

## Read-only report inspection

The checked-in inspector decodes only the fixed report-slot and score fields
from a 131072-byte Pokémon Snap (USA) FlashRAM image. It validates the exact
save version marker, never writes the input, and can emit text or JSON:

```sh
python3 scripts/inspect_snap_save.py '/path/to/pokemonsnap.n64.us.bin'
python3 scripts/inspect_snap_save.py '/path/to/pokemonsnap.n64.us.bin' --json
```

The offsets follow `UnkBigBoy` and the 63-slot `D_800AE4E4` table in the pinned
decomp. This is development evidence only; saves, photos, and decoded private
state remain excluded from commits and diagnostics exports.

## FlashRAM is required

Pokémon Snap uses a 1 Mbit FlashRAM chip: 128 KiB (`0x20000` bytes). The native
game registration must therefore use `recomp::SaveType::Flashram`; `None`,
EEPROM, SRAM, and permissive `AllowAll` are not acceptable substitutes.

The persistent `UnkBigBoy` structure in
`ref/pokemonsnap/src/more_funcs/more_funcs.h` is `0x1F2A4` bytes. It contains
the player name, item and progression flags, records for 69 Pokémon, four
additional photo slots, and 60 album photo/comment entries. Startup routine
`func_800C05D4_5D474` initializes FlashRAM, reads that structure, and validates
both its 16-byte `HAL_SNAP_V1.0-1` marker and MD4 digest. Invalid or erased data
causes a fresh structure to be initialized.

Save routine `func_800BF244_5C0E4` stamps `osGetTime`, updates the digest, and
writes the whole structure. Confirmed game-level save paths include:

- Professor Oak's explicit save prompt after photo review;
- the Oak's Lab exit save path; and
- Gallery/album changes.

N64ModernRuntime allocates `0x20000` bytes for `SaveType::Flashram`, initializes
new storage to `0xFF`, and persists it asynchronously to
`<config>/saves/<game_id>.bin` through its backup-aware output path. SnapPad's
reviewed runtime patch also permits a range ending exactly at the buffer
boundary, which is required by `osFlashAllErase_recomp` clearing
`[0, 0x20000)`. It deliberately does not carry Paper Mario's game-specific
out-of-range FlashRAM page wrapping.

## Default controller-port policy

The executable policy in `port/runtime/accessory_policy.cpp` is:

| N64 port | Device | Accessory | Reason |
| --- | --- | --- | --- |
| 1 | Standard controller | None | Required single-player input; touch, keyboard, or assigned physical controller feeds this port. |
| 2 | Absent | None | Pokémon Snap is single-player. |
| 3 | Absent | None | Pokémon Snap is single-player. |
| 4 | Absent | None | Keeps the optional Pokémon Snap Station printer unavailable. |

Pokémon Snap's controller manager probes printer, Transfer/Game Boy Pak,
Rumble Pak, and Controller Pak devices. The printer is recognized only in port
4, and Gallery UI disables printing when it is absent. Transfer Pak routines
have no external game call sites in the current source, while Controller Pak
support is not needed for progression.

N64ModernRuntime currently models only no pak and Rumble Pak. Its Controller
Pak operations report `PFS_ERR_NOPACK`; Controller Pak and Transfer Pak device
types are not enabled. Returning no pak also avoids setting `CONT_CARD_ON`, so
Pokémon Snap does not enter unavailable accessory paths. This is safer and
more truthful than claiming hardware that is not implemented.

Rumble is optional, not a baseline blocker. The source defines start/stop/init
helpers, but the only found game call sites initialize and stop rumble during
pre-NMI reset; no gameplay `contRumbleStart` call site was found. It may be
enabled later only after runtime observation proves correct detection and no
regression.

## Required runtime evidence

After G1/G2 produce a runnable game, acceptance requires all of the following:

1. Register the game as `recomp::SaveType::Flashram` and verify a fresh launch
   creates or initializes an exact `0x20000`-byte backing file.
2. Start a new game, set a player name, complete the tutorial/course return,
   accept Oak's save prompt, exit cleanly, relaunch, and verify name,
   progression, and saved photos survive.
3. Modify the album in Gallery, save, relaunch, and verify the album entry and
   comment survive.
4. Interrupt or rapidly repeat saves and verify the backup-aware writer leaves
   a loadable current or backup file without truncation.
5. Launch with ports 2–4 and every accessory absent; enter Oak's Lab and
   Gallery, exercise the disabled print UI, and verify no probe hangs or false
   device state.
6. Exercise full-chip initialization/erase and the highest valid FlashRAM page
   under AddressSanitizer where practical; verify there is no assertion or
   out-of-bounds access.
7. If rumble is later enabled, repeat save, Gallery, disconnect/reconnect, and
   pre-NMI reset tests with and without a physical controller.

Until that matrix passes on both macOS and a physical iPad, persistence and
accessory support remain unaccepted.

## Observed macOS first-play persistence

On 2026-08-26 the ARM64 macOS app completed the first-play review path and the
explicit Oak's Lab save prompt. The current backing file is exactly 131072
bytes and has SHA-256
`fbb8b092ba09ccaafe912cba27a82b80a51c4412591c81d1886793a30086dbb8`;
its backup is also 131072 bytes. A clean production relaunch, with the bounded
camera-test and score-trace environment variables removed, exposed Continue
and loaded a Pokémon Report containing Pidgey, 1 kind, and 1400 points.

This closes the macOS portion of required-evidence items 1 and 2 for G5 only.
It does not yet prove repeated-save recovery, erase/new-game behavior, album
comments, the highest FlashRAM page, Simulator persistence, or physical iPad
persistence.
