#!/usr/bin/env python3
"""Generate SnapPad's N64Recomp config from verified rebuild artifacts.

This intentionally contains no game addresses. The entrypoint, zero-sized
function lengths, and dead-symbol ignores are derived from the rebuilt ELF.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "dependencies.lock.json"
EVIDENCE = ROOT / "generated/evidence/G1.json"
DECOMP = ROOT / "ref/pokemonsnap"
ELF = DECOMP / "build/pokemonsnap.elf"
MAP = DECOMP / "build/pokemonsnap.map"
ROM = ROOT / "generated/rom/pokemonsnap.z64"
SPLAT = DECOMP / "splat.yaml"
READELF = ROOT / "build-tools/mips-binutils-2.46.1/bin/mips-linux-gnu-readelf"
OBJDUMP = ROOT / "build-tools/mips-binutils-2.46.1/bin/mips-linux-gnu-objdump"
OUT = ROOT / "generated/aot/snappad-us.toml"
METADATA_OUT = ROOT / "generated/aot/snappad_game_metadata.h"
OUTPUT_FUNCS = ROOT / "generated/aot/snappad_recomp_out"
RSP_TEXT_SYMBOLS = (
    "rspbootTextStart",
    "rspbootTextEnd",
    "aspMainTextStart",
    "aspMainTextEnd",
    "gspF3DEX2_NoN_fifoTextStart",
    "gspF3DEX2_NoN_fifoTextEnd",
    "gspL3DEX2_fifoTextStart",
    "gspL3DEX2_fifoTextEnd",
)
# rspbootTextStart and gspL3DEX2_fifoTextStart are already in N64Recomp's
# built-in ignored list; zero-sized End labels never become generated funcs.
RSP_CONFIG_IGNORES = (
    "aspMainTextStart",
    "gspF3DEX2_NoN_fifoTextStart",
)
# N64ModernRuntime replaces osCreateViManager and owns the host VI event loop.
# The original private thread entry must therefore remain unreachable; compiling
# it would incorrectly pull in hardware-only libultra interrupt internals.
RUNTIME_OWNED_HIDDEN_FUNCTIONS = frozenset({"viMgrMain"})
# IDO omitted this static callback from both the final ELF and the input-object
# symbol table. The source declaration, the object's executable prefix, and
# sprintf's relocation of `.text+0` as the _Printf callback agree on the exact
# object-relative range. Keep the exception relative to the link-map object so
# ROM relocation still fails closed instead of embedding a game address.
VERIFIED_ANONYMOUS_OBJECT_FUNCTIONS = {
    "build/ultralib/src/libc/sprintf.c.o": (("proutSprintf", 0x0, 0x24),),
}


def fail(message: str) -> "NoReturn":
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(1)


def run_readelf(*args: str) -> str:
    try:
        return subprocess.run(
            [str(READELF), *args, str(ELF)],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    except subprocess.CalledProcessError as exc:
        fail(f"readelf failed: {exc.stderr.strip()}")


def sha1(path: Path) -> str:
    digest = hashlib.sha1()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_internal_name(rom: Path) -> str:
    with rom.open("rb") as stream:
        stream.seek(0x20)
        raw_name = stream.read(20)
    if len(raw_name) != 20:
        fail("normalized ROM is too short to contain an N64 internal name")
    try:
        name = raw_name.decode("ascii").rstrip(" \0")
    except UnicodeDecodeError:
        fail("normalized ROM internal name is not ASCII")
    if not name or any(ord(character) < 0x20 or ord(character) > 0x7E for character in name):
        fail(f"normalized ROM has an invalid internal name: {name!r}")
    return name


def render_game_metadata(
    rom_xxh3: str,
    internal_name: str,
    entrypoint: int,
    sp_imem_ok_vram: int,
    sp_dmem_ok_vram: int,
    player_focus_flag_vram: int,
    player_focus_object_vram: int,
    player_focus_subject_vram: int,
) -> str:
    if re.fullmatch(r"0x[0-9A-F]{16}", rom_xxh3) is None:
        fail(f"G1 evidence contains invalid ROM XXH3: {rom_xxh3!r}")
    escaped_name = internal_name.replace("\\", "\\\\").replace('"', '\\"')
    return f'''#pragma once

#include <cstdint>

namespace pokemon_snap::generated {{

inline constexpr std::uint64_t rom_xxh3 = {rom_xxh3}ULL;
inline constexpr std::uint32_t entrypoint = 0x{entrypoint:08X}U;
inline constexpr std::uint32_t sp_imem_ok_vram = 0x{sp_imem_ok_vram:08X}U;
inline constexpr std::uint32_t sp_dmem_ok_vram = 0x{sp_dmem_ok_vram:08X}U;
inline constexpr std::uint32_t player_focus_flag_vram = 0x{player_focus_flag_vram:08X}U;
inline constexpr std::uint32_t player_focus_object_vram = 0x{player_focus_object_vram:08X}U;
inline constexpr std::uint32_t player_focus_subject_vram = 0x{player_focus_subject_vram:08X}U;
inline constexpr std::uint32_t illegal_copy_player_flag = 21U;
inline constexpr char internal_name[] = "{escaped_name}";
inline constexpr char8_t game_id[] = u8"pokemonsnap.n64.us";

}} // namespace pokemon_snap::generated
'''


def read_sections() -> dict[int, tuple[str, int, int]]:
    sections: dict[int, tuple[str, int, int]] = {}
    pattern = re.compile(
        r"^\s*\[\s*(\d+)\]\s+(\S+)\s+\S+\s+"
        r"([0-9a-fA-F]+)\s+[0-9a-fA-F]+\s+([0-9a-fA-F]+)"
    )
    for line in run_readelf("-SW").splitlines():
        match = pattern.match(line)
        if match:
            sections[int(match.group(1))] = (
                match.group(2),
                int(match.group(3), 16),
                int(match.group(4), 16),
            )
    if not sections:
        fail("ELF has no readable sections")
    return sections


def read_symbols() -> list[tuple[int, int, str, str, str, str]]:
    return parse_symbols(run_readelf("-sW"))


def parse_symbols(output: str) -> list[tuple[int, int, str, str, str, str]]:
    symbols = []
    for line in output.splitlines():
        fields = line.split()
        if len(fields) < 8 or not fields[0].rstrip(":").isdigit():
            continue
        symbols.append(
            (
                int(fields[1], 16),
                # GNU readelf normally prints st_size in decimal, but uses a
                # 0x prefix for a handful of large/absolute MIPS symbols.
                int(fields[2], 0),
                fields[3],
                fields[4],
                fields[6],
                fields[7],
            )
        )
    if not symbols:
        fail("ELF has no readable symbols")
    return symbols


def read_object_symbols(path: Path) -> list[tuple[int, int, str, str, str, str]]:
    try:
        output = subprocess.run(
            [str(READELF), "-sW", str(path)],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    except subprocess.CalledProcessError as exc:
        fail(f"readelf failed for {path}: {exc.stderr.strip()}")
    return parse_symbols(output)


def run_objdump_range(start: int, end: int) -> str:
    try:
        return subprocess.run(
            [
                str(OBJDUMP),
                "-d",
                f"--start-address=0x{start:X}",
                f"--stop-address=0x{end:X}",
                str(ELF),
            ],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    except subprocess.CalledProcessError as exc:
        fail(f"objdump failed while recovering call targets: {exc.stderr.strip()}")


def read_linked_jal_targets(start: int, end: int) -> set[int]:
    """Return direct-call destinations inside one linked input-object range."""
    output = run_objdump_range(start, end)
    return {
        int(match.group(1), 16)
        for match in re.finditer(r"\bjal\s+([0-9A-Fa-f]+)\b", output)
        if start <= int(match.group(1), 16) < end
    }


def derive_ai_length_read_patches(
    symbols: list[tuple[int, int, str, str, str, str]],
) -> list[tuple[int, int]]:
    """Find auThreadMain's direct AI_LEN reads and encode runtime-backed moves.

    Pokémon Snap reads AI_LEN_REG directly in two places instead of calling
    osAiGetLength. On a native host those KSEG1 MMIO addresses are not memory.
    Find the exact `lui reg, 0xA450` + `lw dest, 4(reg)` sequences in the rebuilt
    ELF and replace each load with `or dest, v0, zero`; a generated text hook
    calls N64ModernRuntime's existing osAiGetLength model immediately before it.
    """
    functions = [
        (value, size)
        for value, size, typ, _bind, ndx, name in symbols
        if name == "auThreadMain" and typ == "FUNC" and ndx != "UND" and size > 0
    ]
    if len(functions) != 1:
        fail(f"expected one sized auThreadMain function, found {len(functions)}")
    start, size = functions[0]
    instructions: list[tuple[int, int]] = []
    for line in run_objdump_range(start, start + size).splitlines():
        match = re.match(r"^\s*([0-9A-Fa-f]+):\s+([0-9A-Fa-f]{8})\s+", line)
        if match:
            instructions.append((int(match.group(1), 16), int(match.group(2), 16)))

    patches: list[tuple[int, int]] = []
    for index, (_address, word) in enumerate(instructions):
        opcode = word >> 26
        if opcode != 0x0F or (word & 0xFFFF) != 0xA450:  # LUI base, AI register page
            continue
        base_register = (word >> 16) & 31
        for load_address, load_word in instructions[index + 1:index + 6]:
            if (
                load_word >> 26 == 0x23  # LW
                and (load_word >> 21) & 31 == base_register
                and load_word & 0xFFFF == 4  # AI_LEN_REG
            ):
                destination = (load_word >> 16) & 31
                move_from_v0 = (2 << 21) | (destination << 11) | 0x25
                patches.append((load_address, move_from_v0))
                break
    patches = sorted(set(patches))
    if len(patches) != 2:
        fail(f"expected two direct AI length reads in auThreadMain, found {len(patches)}")
    return patches


def derive_photo_score_fallback_metadata(
    symbols: list[tuple[int, int, str, str, str, str]],
) -> tuple[int, int]:
    """Find the score-wrapper epilogue and its saved PhotoData argument."""
    function_name = "func_8037452C_847CDC"
    functions = [
        (value, size)
        for value, size, typ, _bind, ndx, name in symbols
        if name == function_name and typ == "FUNC" and ndx != "UND" and size > 0
    ]
    if len(functions) != 1:
        fail(f"expected one sized photo score wrapper, found {len(functions)}")

    start, size = functions[0]
    instructions: list[tuple[int, int]] = []
    for line in run_objdump_range(start, start + size).splitlines():
        match = re.match(r"^\s*([0-9A-Fa-f]+):\s+([0-9A-Fa-f]{8})\s+", line)
        if match:
            instructions.append((int(match.group(1), 16), int(match.group(2), 16)))

    photo_slots = {
        word & 0xFFFF
        for _address, word in instructions
        if word >> 26 == 0x2B
        and (word >> 21) & 31 == 29
        and (word >> 16) & 31 == 5
    }
    if len(photo_slots) != 1:
        fail(f"expected one saved PhotoData stack slot, found {len(photo_slots)}")

    epilogues = []
    for index, (address, word) in enumerate(instructions[:-2]):
        next_word = instructions[index + 1][1]
        return_word = instructions[index + 2][1]
        if (
            word >> 26 == 0x23
            and (word >> 21) & 31 == 29
            and (word >> 16) & 31 == 31
            and next_word >> 26 == 0x09
            and (next_word >> 21) & 31 == 29
            and (next_word >> 16) & 31 == 29
            and (next_word & 0x8000) == 0
            and return_word == 0x03E00008
        ):
            epilogues.append(address)
    if len(epilogues) != 1:
        fail(f"expected one photo score wrapper epilogue, found {len(epilogues)}")
    return epilogues[0], next(iter(photo_slots))


def derive_photo_capture_metadata(
    symbols: list[tuple[int, int, str, str, str, str]],
) -> tuple[int, int, int, int]:
    """Derive focus globals and the post-copy observation point."""
    make_photo = [
        value for value, size, typ, _bind, ndx, name in symbols
        if name == "makePhoto" and typ == "FUNC" and ndx != "UND" and size > 0
    ]
    if len(make_photo) != 1:
        fail(f"expected one sized makePhoto function, found {len(make_photo)}")

    copy_info = [
        (value, size) for value, size, typ, _bind, ndx, name in symbols
        if name == "PokemonDetector_CopyInfo"
        and typ == "FUNC" and ndx != "UND" and size == 0x7C
    ]
    if len(copy_info) != 1:
        fail(
            "expected one 0x7c-byte PokemonDetector_CopyInfo function, "
            f"found {len(copy_info)}"
        )

    globals_by_name: dict[str, int] = {}
    for name in (
        "gHasPokemonInFocus", "gPokemonInFocus", "gPokemonIdInFocus"
    ):
        matches = [
            value for value, _size, typ, _bind, ndx, symbol_name in symbols
            if symbol_name == name and typ == "OBJECT" and ndx != "UND"
        ]
        if len(matches) != 1:
            fail(f"expected one defined {name} object, found {len(matches)}")
        globals_by_name[name] = matches[0]
    return (
        globals_by_name["gHasPokemonInFocus"],
        globals_by_name["gPokemonInFocus"],
        globals_by_name["gPokemonIdInFocus"],
        copy_info[0][0] + 0x4C,
    )


def read_text_object_ranges() -> dict[str, list[tuple[int, int, str]]]:
    """Read linked input-object text bounds, grouped by ELF output section."""
    ranges: dict[str, list[tuple[int, int, str]]] = {}
    current_section: str | None = None
    in_memory_map = False
    for line in MAP.read_text(encoding="utf-8", errors="replace").splitlines():
        if line == "Linker script and memory map":
            in_memory_map = True
            continue
        if not in_memory_map:
            continue
        output = re.match(
            r"^(\.[A-Za-z0-9_]+)\s+0x[0-9A-Fa-f]+\s+0x[0-9A-Fa-f]+",
            line,
        )
        if output:
            current_section = output.group(1)
        text = re.match(
            r"^\s+\.text\s+0x([0-9A-Fa-f]+)\s+0x([0-9A-Fa-f]+)\s+(\S+\.o)$",
            line,
        )
        if text and current_section:
            start = int(text.group(1), 16)
            size = int(text.group(2), 16)
            if size:
                ranges.setdefault(current_section, []).append(
                    (start, start + size, text.group(3))
                )
    if not ranges:
        fail("linker map exposes no input-object text ranges")
    return ranges


def derive_entrypoint(symbols: list[tuple[int, int, str, str, str, str]]) -> int:
    header = run_readelf("-h")
    match = re.search(r"Entry point address:\s*(0x[0-9a-fA-F]+)", header)
    if not match:
        fail("ELF header does not expose an entrypoint")
    header_entry = int(match.group(1), 16)

    # The linker intentionally leaves e_entry at zero and spimdisasm names the
    # first function by address. Derive its VRAM from the audited Splat segment
    # containing the `entry` assembly file, then require a unique FUNC there.
    splat_text = SPLAT.read_text(encoding="utf-8")
    segment_match = re.search(
        r"(?ms)^  - name:\s*main\s*$"
        r"(?P<body>.*?)(?=^  - (?:name:|\[)|\Z)",
        splat_text,
    )
    if segment_match is None:
        fail("splat.yaml no longer contains the main code segment")
    body = segment_match.group("body")
    start_match = re.search(r"^    start:\s*(0x[0-9A-Fa-f]+)\s*$", body, re.MULTILINE)
    vram_match = re.search(r"^    vram:\s*(0x[0-9A-Fa-f]+)\s*$", body, re.MULTILINE)
    entry_match = re.search(
        r"^    - \[\s*(0x[0-9A-Fa-f]+)\s*,\s*hasm\s*,\s*entry\s*\]\s*$",
        body,
        re.MULTILINE,
    )
    if start_match is None or vram_match is None or entry_match is None:
        fail("main segment no longer provides start, VRAM, and entry metadata")
    segment_start = int(start_match.group(1), 16)
    segment_vram = int(vram_match.group(1), 16)
    entry_rom = int(entry_match.group(1), 16)
    if entry_rom < segment_start:
        fail("entry subsegment precedes the main segment")
    rom_entry = segment_vram + entry_rom - segment_start
    candidates = [
        (value, name)
        for value, _size, typ, _bind, ndx, name in symbols
        if typ == "FUNC" and ndx != "UND" and value == rom_entry
    ]
    if len(candidates) != 1:
        fail(
            f"expected one defined FUNC at derived entrypoint 0x{rom_entry:08X}, "
            f"found {len(candidates)}"
        )
    symbol_entry, _symbol_name = candidates[0]
    if header_entry not in (0, symbol_entry):
        fail(
            f"ELF header entrypoint 0x{header_entry:08X} conflicts with "
            f"entry symbol 0x{symbol_entry:08X}"
        )
    if not 0x80000000 <= symbol_entry <= 0x807FFFFF:
        fail(f"entry symbol is outside N64 cached RDRAM: 0x{symbol_entry:08X}")
    return symbol_entry


def derive_function_sizes(
    symbols: list[tuple[int, int, str, str, str, str]],
    sections: dict[int, tuple[str, int, int]],
    object_ranges: dict[str, list[tuple[int, int, str]]] | None = None,
) -> list[tuple[str, int]]:
    by_section: dict[int, list[tuple[int, int, str, str]]] = {}
    for value, size, typ, _bind, ndx, name in symbols:
        if not ndx.isdigit() or int(ndx) not in sections:
            continue
        if value == 0 and typ == "SECTION":
            continue
        by_section.setdefault(int(ndx), []).append((value, size, name, typ))

    derived: list[tuple[str, int]] = []
    for section_index, entries in by_section.items():
        section_name, section_address, section_size = sections[section_index]
        entries.sort(key=lambda item: (item[0], item[2]))
        symbol_rows = [
            row for row in symbols
            if row[4].isdigit() and int(row[4]) == section_index
        ]
        binding_by_identity = {
            (value, name): bind for value, _size, _typ, bind, _ndx, name in symbol_rows
        }
        for index, (value, size, name, typ) in enumerate(entries):
            if (
                typ != "FUNC"
                or size != 0
                or name.startswith("._")
                or name.endswith("TextEnd")
                or binding_by_identity.get((value, name)) == "LOCAL"
            ):
                continue
            later_addresses = [entry[0] for entry in entries[index + 1:] if entry[0] > value]
            boundary = section_address + section_size
            if object_ranges is not None:
                containing = [
                    end
                    for start, end, _path in object_ranges.get(section_name, [])
                    if start <= value < end
                ]
                if len(containing) != 1:
                    print(
                        f"warning: could not bind {name} to one text object",
                        file=sys.stderr,
                    )
                    continue
                boundary = containing[0]
            next_address = min(
                [address for address in later_addresses if address <= boundary]
                or [boundary]
            )
            function_size = next_address - value
            if function_size > 0 and function_size % 4 == 0:
                derived.append((name, function_size))
            else:
                print(
                    f"warning: could not size {name} at 0x{value:08X}",
                    file=sys.stderr,
                )

    unique: dict[str, int] = {}
    for name, size in derived:
        if name in unique and unique[name] != size:
            fail(f"ambiguous derived sizes for function {name}")
        unique.setdefault(name, size)
    return sorted(unique.items())


def derive_manual_functions(
    symbols: list[tuple[int, int, str, str, str, str]],
    sections: dict[int, tuple[str, int, int]],
    object_ranges: dict[str, list[tuple[int, int, str]]],
) -> list[tuple[str, str, int, int]]:
    """Recover IDO local functions omitted or reduced to linker assignments.

    The old IDO object format used by this decomp can emit a function body in
    an object's .text while leaving its static symbol undefined with a nonzero
    st_size. The linker script then supplies the address, producing an ABS
    NOTYPE symbol with size zero in the final ELF. In some objects no final
    symbol survives at all, but the ordered undefined NOTYPE records still
    describe function bodies that fill otherwise-unclaimed parts of .text.
    Require object sizes, known function intervals, and link-map bounds to
    agree before telling N64Recomp about an otherwise invisible function.
    """
    absolute_addresses = {
        name: value
        for value, _size, typ, bind, ndx, name in symbols
        if ndx == "ABS" and typ == "NOTYPE" and bind != "LOCAL"
    }
    section_names = {name for name, _address, _size in sections.values()}
    candidates: list[tuple[str, str, int, int, bool]] = []
    for section_name, ranges in object_ranges.items():
        if section_name not in section_names:
            continue
        for start, end, object_name in ranges:
            object_path = Path(object_name)
            if not object_path.is_absolute():
                object_path = DECOMP / object_path
            if not object_path.is_file():
                fail(f"linker-map text object is missing: {object_path}")
            object_symbols = read_object_symbols(object_path)
            object_manuals: list[tuple[str, int, int]] = []
            for name, offset, size in VERIFIED_ANONYMOUS_OBJECT_FUNCTIONS.get(
                object_name, ()
            ):
                address = start + offset
                if (
                    offset < 0
                    or size <= 0
                    or size % 4 != 0
                    or address + size > end
                ):
                    fail(
                        f"verified anonymous function {name} does not fit its text object: "
                        f"0x{address:08X}+0x{size:X} outside 0x{start:08X}..0x{end:08X}"
                    )
                overlaps_defined = any(
                    typ == "FUNC"
                    and ndx != "UND"
                    and symbol_size > 0
                    and start + value < address + size
                    and start + value + symbol_size > address
                    for value, symbol_size, typ, _bind, ndx, _symbol_name
                    in object_symbols
                )
                if overlaps_defined:
                    fail(f"verified anonymous function {name} overlaps a defined function")
                object_manuals.append((name, address, size))
                candidates.append((name, section_name, address, size, False))
            for _value, size, _typ, _bind, ndx, name in object_symbols:
                address = absolute_addresses.get(name)
                if ndx != "UND" or size <= 0 or address is None:
                    continue
                # An undefined declaration can also be an ordinary reference
                # to a function owned by another object. Only the object whose
                # linked text range contains the supplied address owns it.
                if not (start <= address < end):
                    continue
                if size % 4 != 0 or address + size > end:
                    fail(
                        f"address-backed function {name} does not fit its text object: "
                        f"0x{address:08X}+0x{size:X} outside 0x{start:08X}..0x{end:08X}"
                    )
                object_manuals.append((name, address, size))
                candidates.append((name, section_name, address, size, True))

            known_intervals = [
                (start + value, start + value + size)
                for value, size, typ, _bind, ndx, _name in object_symbols
                if typ == "FUNC" and ndx != "UND" and size > 0
                and value >= 0 and start + value + size <= end
            ]
            known_intervals.extend(
                (address, address + size)
                for _name, address, size in object_manuals
            )
            represented_names = {
                name
                for _value, size, typ, _bind, ndx, name in object_symbols
                if typ == "FUNC" and ndx != "UND" and size > 0
            } | {name for name, _address, _size in object_manuals} \
                | RUNTIME_OWNED_HIDDEN_FUNCTIONS
            hidden = infer_hidden_object_functions(
                object_symbols,
                represented_names,
                known_intervals,
                start,
                end,
                read_linked_jal_targets(start, end),
            )
            candidates.extend(
                (name, section_name, address, size, False)
                for name, address, size in hidden
            )

    by_identity: dict[tuple[str, int], tuple[str, str, int, int, bool]] = {}
    for candidate in candidates:
        identity = (candidate[1], candidate[2])
        previous = by_identity.get(identity)
        if previous is not None and previous[:4] != candidate[:4]:
            fail(f"ambiguous recovered function at 0x{candidate[2]:08X}")
        by_identity[identity] = candidate

    ordered = sorted(by_identity.values(), key=lambda item: (item[2], item[1]))
    name_counts: dict[str, int] = {}
    for name, _section, _address, _size, _address_backed in ordered:
        name_counts[name] = name_counts.get(name, 0) + 1
    return [
        (
            name if address_backed or name_counts[name] == 1 else f"{name}_{address:08X}",
            section,
            address,
            size,
        )
        for name, section, address, size, address_backed in ordered
    ]


def infer_hidden_object_functions(
    object_symbols: list[tuple[int, int, str, str, str, str]],
    represented_names: set[str],
    known_intervals: list[tuple[int, int]],
    start: int,
    end: int,
    entrypoint_hints: set[int] | None = None,
) -> list[tuple[str, int, int]]:
    """Place absent IDO pseudo-functions into tightly matching .text gaps.

    Ordinary undefined references can also carry a size in these objects, so
    recovery is deliberately conservative: every candidate must be absent
    from the linked symbol table, candidates must account for at least 75% of
    the unclaimed object text, preserve symbol-table order, and leave no more
    than 0x50 bytes of alignment/padding in any gap they occupy.
    """
    if start >= end:
        return []
    pseudo_functions = [
        (name, size)
        for _value, size, typ, _bind, ndx, name in object_symbols
        if ndx == "UND" and typ == "NOTYPE" and size > 0 and size % 4 == 0
        # A same-named function can legitimately exist in another input
        # object: these are static SDK helpers whose old object format lost
        # local binding. Skip only a body already represented in this object.
        and name not in represented_names
    ]
    if not pseudo_functions:
        return []

    clipped = sorted(
        (max(start, interval_start), min(end, interval_end))
        for interval_start, interval_end in known_intervals
        if interval_start < end and interval_end > start
    )
    merged: list[tuple[int, int]] = []
    for interval_start, interval_end in clipped:
        if interval_start >= interval_end:
            continue
        if merged and interval_start < merged[-1][1]:
            fail(
                "known function intervals overlap while recovering hidden "
                f"functions in 0x{start:08X}..0x{end:08X}"
            )
        if merged and interval_start == merged[-1][1]:
            merged[-1] = (merged[-1][0], interval_end)
        else:
            merged.append((interval_start, interval_end))

    gaps: list[tuple[int, int]] = []
    cursor = start
    for interval_start, interval_end in merged:
        if cursor < interval_start:
            gaps.append((cursor, interval_start))
        cursor = max(cursor, interval_end)
    if cursor < end:
        gaps.append((cursor, end))

    uncovered = sum(gap_end - gap_start for gap_start, gap_end in gaps)
    candidate_bytes = sum(size for _name, size in pseudo_functions)
    if (
        uncovered == 0
        or candidate_bytes > uncovered
        or candidate_bytes * 4 < uncovered * 3
    ):
        return []

    # Old IDO symbol-table order is usually code order, but seqplayer is a
    # known counterexample. Direct JAL destinations provide stronger evidence:
    # match each hinted entry to the next entry/boundary by the recorded size.
    hints = entrypoint_hints or set()
    hinted_segments: list[tuple[int, int]] = []
    for gap_start, gap_end in gaps:
        entries = sorted(address for address in hints if gap_start <= address < gap_end)
        for index, address in enumerate(entries):
            boundary = entries[index + 1] if index + 1 < len(entries) else gap_end
            hinted_segments.append((address, boundary - address))
    pre_recovered: list[tuple[str, int, int]] = []
    if hinted_segments:
        remaining = list(pseudo_functions)
        hinted: list[tuple[str, int, int]] = []
        claimed: list[tuple[int, int]] = []
        for address, span in hinted_segments:
            exact = [
                (index, name, size)
                for index, (name, size) in enumerate(remaining)
                if size == span
            ]
            matches = exact or [
                (index, name, size)
                for index, (name, size) in enumerate(remaining)
                if size < span and span - size <= 0x50
            ]
            if len(matches) != 1:
                continue
            index, name, size = matches[0]
            hinted.append((name, address, size))
            claimed.append((address, address + span))
            del remaining[index]
        if not remaining:
            return sorted(hinted, key=lambda item: item[1])
        if hinted:
            reduced_gaps: list[tuple[int, int]] = []
            for gap_start, gap_end in gaps:
                cursor = gap_start
                for claimed_start, claimed_end in claimed:
                    if claimed_end <= cursor or claimed_start >= gap_end:
                        continue
                    if cursor < claimed_start:
                        reduced_gaps.append((cursor, claimed_start))
                    cursor = max(cursor, claimed_end)
                if cursor < gap_end:
                    reduced_gaps.append((cursor, gap_end))
            gaps = reduced_gaps
            pseudo_functions = remaining
            pre_recovered = hinted

    recovered: list[tuple[str, int, int]] = list(pre_recovered)
    candidate_index = 0
    for gap_start, gap_end in gaps:
        if candidate_index == len(pseudo_functions):
            break
        gap_size = gap_end - gap_start
        used = 0
        first_index = candidate_index
        while candidate_index < len(pseudo_functions):
            name, size = pseudo_functions[candidate_index]
            if used + size > gap_size:
                break
            recovered.append((name, gap_start + used, size))
            used += size
            candidate_index += 1
        if used and gap_size - used > 0x50:
            del recovered[-(candidate_index - first_index):]
            return []

    if candidate_index != len(pseudo_functions):
        return []
    return sorted(recovered, key=lambda item: item[1])


def derive_unique_symbol(
    symbols: list[tuple[int, int, str, str, str, str]], name: str
) -> int:
    candidates = [
        value
        for value, _size, _typ, _bind, ndx, symbol_name in symbols
        if ndx != "UND" and symbol_name == name
    ]
    if len(candidates) != 1:
        fail(f"expected one defined symbol named {name}, found {len(candidates)}")
    return candidates[0]


def main() -> None:
    for path, label in ((READELF, "local readelf"), (OBJDUMP, "local objdump"),
                        (ELF, "rebuilt ELF"),
                        (MAP, "rebuilt linker map"), (ROM, "normalized ROM"),
                        (SPLAT, "decomp segment map"), (EVIDENCE, "G1 evidence")):
        if not path.is_file() or path.stat().st_size == 0:
            fail(f"missing {label}: {path}")

    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    expected_sha1 = lock["rom"]["sha1"]
    actual_sha1 = sha1(ROM)
    if actual_sha1 != expected_sha1:
        fail(f"normalized ROM SHA-1 mismatch: {actual_sha1}")

    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    if not evidence.get("exactRebuild") or evidence.get("lockedRomSha1") != expected_sha1:
        fail("G1 evidence does not certify the locked exact rebuild")
    expected_artifacts = {
        "normalizedRom": ROM,
        "elf": ELF,
        "linkerMap": MAP,
    }
    for key, path in expected_artifacts.items():
        recorded = evidence.get(key, {}).get("sha256")
        if recorded != sha256(path):
            fail(f"G1 evidence no longer matches {key}: {path}")

    sections = read_sections()
    symbols = read_symbols()
    entrypoint = derive_entrypoint(symbols)
    if evidence.get("derivedEntrypoint") != f"0x{entrypoint:08X}":
        fail("G1 evidence entrypoint no longer matches the rebuilt ELF")
    object_ranges = read_text_object_ranges()
    sizes = derive_function_sizes(symbols, sections, object_ranges)
    manual_functions = derive_manual_functions(symbols, sections, object_ranges)
    ai_length_patches = derive_ai_length_read_patches(symbols)
    photo_score_hook, photo_score_photo_stack_offset = (
        derive_photo_score_fallback_metadata(symbols)
    )
    (player_focus_flag_vram, player_focus_object_vram,
     player_focus_subject_vram, focus_observe_hook) = (
        derive_photo_capture_metadata(symbols)
    )
    sp_imem_ok_vram = derive_unique_symbol(symbols, "gSPImemOkay")
    sp_dmem_ok_vram = derive_unique_symbol(symbols, "gSPDmemOkay")
    # electrode_WaitForPlayer has just loaded getLevelProgress's block into v0
    # and fraction into f4 at +0x48. Trace that verified decision point rather
    # than inferring the hidden-path window from elapsed host time.
    tunnel_progress_hook = (
        derive_unique_symbol(symbols, "electrode_WaitForPlayer") + 0x48
    )
    # Icons_Init calls getProgressFlags at +0x8; the first instruction after
    # the call/delay slot is +0x10, where v0 still contains the returned flags.
    icons_acceptance_item_hook = derive_unique_symbol(symbols, "Icons_Init") + 0x10
    derive_unique_symbol(symbols, "electrode_HiddenPathGuardIdle")
    derive_unique_symbol(symbols, "Items_UpdateItemMovement")
    derive_unique_symbol(symbols, "cmdSendCommand")
    derive_unique_symbol(symbols, "electrode_RevealHiddenPath")
    derive_unique_symbol(symbols, "setPlayerFlag")
    derive_unique_symbol(symbols, "func_80364360_504770")
    for name in RSP_TEXT_SYMBOLS:
        derive_unique_symbol(symbols, name)
    ignored_symbols = sorted(
        {
            name
            for _value, _size, typ, _bind, ndx, name in symbols
            if typ == "FUNC" and ndx.isdigit() and name.startswith("dead_")
        }
        | set(RSP_CONFIG_IGNORES)
    )

    function_sizes = "\n".join(
        f'[[input.function_sizes]]\nname = "{name}"\nsize = 0x{size:X}'
        for name, size in sizes
    )
    manual_function_entries = "\n".join(
        f'[[input.manual_funcs]]\nname = "{name}"\nsection = "{section}"\n'
        f'vram = 0x{address:08X}\nsize = 0x{size:X}'
        for name, section, address, size in manual_functions
    )
    ai_length_entries = "\n\n".join(
        f'[[patches.hook]]\nfunc = "auThreadMain"\n'
        f'before_vram = 0x{address:08X}\n'
        f'text = "osAiGetLength_recomp(rdram, ctx);"\n\n'
        f'[[patches.instruction]]\nfunc = "auThreadMain"\n'
        f'vram = 0x{address:08X}\nvalue = 0x{instruction:08X}'
        for address, instruction in ai_length_patches
    )
    ignores = "\n".join(f'    "{name}",' for name in ignored_symbols)
    config = f'''# Pokemon Snap (USA) N64Recomp generation config.
# Generated from the verified decomp ELF by scripts/generate-n64recomp-config.py.
# Do not add unverified game-specific hooks or addresses here.

[input]
entrypoint = 0x{entrypoint:08X}
elf_path = "{ELF}"
rom_file_path = "{ROM}"
output_func_path = "{OUTPUT_FUNCS}"
recomp_include = "#include \\"recomp.h\\"\\n#include \\"snappad_game_hooks.h\\""

{function_sizes}

{manual_function_entries}

[patches]
# RSP microcode is never CPU-recompiled: audio is generated separately with
# RSPRecomp, while graphics and boot tasks use their documented runtime paths.
ignored = [
{ignores}
]

{ai_length_entries}

# A course can be abandoned before Camera Check. Start each detector session
# with an empty host-side shutter correlation queue so a later trip cannot
# inherit a subject from that abandoned course.
[[patches.hook]]
func = "PokemonDetector_Create"
text = "SnapPad_ResetPhotoCaptureSession(rdram, ctx);"

# Observe the player-facing focus only after CopyInfo has committed its flag,
# object, and subject ID. The trace is test-only and lets acceptance aiming
# wait for the same identity the game will use at the shutter.
[[patches.hook]]
func = "PokemonDetector_CopyInfo"
before_vram = 0x{focus_observe_hook:08X}
text = "SnapPad_ObservePlayerFocus(rdram, ctx);"

# Retain the player-facing focus result at the exact function that commits a
# photo so the native score fallback can recover from an empty Metal readback.
[[patches.hook]]
func = "makePhoto"
text = "SnapPad_CaptureFocusedSubject(rdram, ctx);"

# Acceptance routes can begin on the same level-progress condition that makes
# Tunnel's hidden-path Electrode interactive. At this hook v0 is the block and
# f4 is the fractional progress loaded by electrode_WaitForPlayer.
[[patches.hook]]
func = "electrode_WaitForPlayer"
before_vram = 0x{tunnel_progress_hook:08X}
text = "SnapPad_ObserveTunnelProgress(rdram, ctx);"

# The clean Tunnel acceptance route needs the stock pester-ball interaction,
# but the bundled test save has only the apple unlocked. Temporarily OR the
# pester bit into Icons_Init's returned progress flags when (and only when) the
# explicit Tunnel acceptance environment switch is present. FlashRAM is not
# modified.
[[patches.hook]]
func = "Icons_Init"
before_vram = 0x{icons_acceptance_item_hook:08X}
text = "SnapPad_EnableAcceptancePesterBall(rdram, ctx);"

# Remember the exact GObj that owns Tunnel's hidden-path interaction graph.
# This lets acceptance telemetry distinguish a visual focus hit from the item
# system actually dispatching an impact command to that specific Pokemon.
[[patches.hook]]
func = "electrode_HiddenPathGuardIdle"
text = "SnapPad_ObserveHiddenPathGuard(rdram, ctx);"

# Measure pester-ball closest approach to the exact hidden-path guard during
# native acceptance. This geometry trace is inert unless gameplay tracing is
# explicitly enabled and replaces blind reticle-offset tuning.
[[patches.hook]]
func = "Items_UpdateItemMovement"
text = "SnapPad_ObservePesterTrajectory(rdram, ctx);"

# Trace only the three stock item/proximity commands once the hidden-path guard
# exists. At function entry r4 is the destination GObj and r5 is the command.
[[patches.hook]]
func = "cmdSendCommand"
text = "SnapPad_ObserveCommand(rdram, ctx);"

# Record the authentic interaction handler; this is the acceptance proof that
# the Electrode was struck and the hidden-path cutscene actually began.
[[patches.hook]]
func = "electrode_RevealHiddenPath"
text = "SnapPad_ObserveHiddenPathReveal(rdram, ctx);"

# The game scores photos by rerendering them into an offscreen framebuffer.
# Preserve authentic scores; recover only focus-tagged photos whose native
# Metal readback returned an empty score or the game's unrecognized-ID sentinel.
[[patches.hook]]
func = "func_8037452C_847CDC"
before_vram = 0x{photo_score_hook:08X}
text = "SnapPad_ApplyPhotoScoreFallback(rdram, ctx, MEM_W(0x{photo_score_photo_stack_offset:X}, ctx->r29));"

# This function otherwise decompresses MIPS to 0x80200000 and jumps to it.
# Preserve its observable SP-integrity/illegal-copy contract in native code;
# do not attempt runtime-generated execution on Apple targets.
[[patches.hook]]
func = "func_80364360_504770"
text = "SnapPad_RunSPIntegrityCheck(rdram, ctx); return;"
'''
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(config, encoding="utf-8")
    internal_name = read_internal_name(ROM)
    METADATA_OUT.write_text(
        render_game_metadata(
            evidence.get("romXxh3_64", ""),
            internal_name,
            entrypoint,
            sp_imem_ok_vram,
            sp_dmem_ok_vram,
            player_focus_flag_vram,
            player_focus_object_vram,
            player_focus_subject_vram,
        ),
        encoding="utf-8",
    )
    print(
        f"Wrote {OUT} with entrypoint 0x{entrypoint:08X}, "
        f"{len(sizes)} inferred sizes, {len(manual_functions)} recovered functions, "
        f"and {len(ignored_symbols)} classified ignores."
    )
    print(f"Wrote evidence-checked native game metadata: {METADATA_OUT}")


if __name__ == "__main__":
    main()
