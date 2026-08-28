#!/usr/bin/env python3
"""Read-only summary of a Pokémon Snap (USA) FlashRAM report.

Offsets and the 63 report slots come from UnkBigBoy and D_800AE4E4 in the
pinned Pokémon Snap decomp. This tool never writes the save.
"""

from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path
from typing import Any


FLASH_SIZE = 0x20000
SAVE_DATA_SIZE = 0x1F2A4
VERSION_OFFSET = 0x10
VERSION = b"HAL_SNAP_V1.0-1\0"
SCORE_TABLE_OFFSET = 0x6C
PHOTO_TABLE_OFFSET = 0x180
PHOTO_SIZE = 0x3A0
PHOTO_VALID_OFFSET = 0x04

# Report-slot order from the exact D_800AE4E4 table. Pokémon absent from the
# N64 game intentionally have no slot.
REPORT_SPECIES = (
    (1, "Bulbasaur"), (4, "Charmander"), (5, "Charmeleon"),
    (6, "Charizard"), (7, "Squirtle"), (11, "Metapod"),
    (12, "Butterfree"), (14, "Kakuna"), (16, "Pidgey"),
    (25, "Pikachu"), (27, "Sandshrew"), (28, "Sandslash"),
    (37, "Vulpix"), (39, "Jigglypuff"), (41, "Zubat"),
    (45, "Vileplume"), (50, "Diglett"), (51, "Dugtrio"),
    (52, "Meowth"), (54, "Psyduck"), (56, "Mankey"),
    (58, "Growlithe"), (59, "Arcanine"), (60, "Poliwag"),
    (70, "Weepinbell"), (71, "Victreebel"), (74, "Geodude"),
    (75, "Graveler"), (78, "Rapidash"), (79, "Slowpoke"),
    (80, "Slowbro"), (81, "Magnemite"), (82, "Magneton"),
    (84, "Doduo"), (88, "Grimer"), (89, "Muk"),
    (90, "Shellder"), (91, "Cloyster"), (93, "Haunter"),
    (101, "Electrode"), (109, "Koffing"), (113, "Chansey"),
    (115, "Kangaskhan"), (118, "Goldeen"), (120, "Staryu"),
    (121, "Starmie"), (123, "Scyther"), (124, "Jynx"),
    (125, "Electabuzz"), (126, "Magmar"), (129, "Magikarp"),
    (130, "Gyarados"), (131, "Lapras"), (132, "Ditto"),
    (133, "Eevee"), (137, "Porygon"), (143, "Snorlax"),
    (144, "Articuno"), (145, "Zapdos"), (146, "Moltres"),
    (147, "Dratini"), (149, "Dragonite"), (151, "Mew"),
)


def inspect_save(path: Path) -> dict[str, Any]:
    payload = path.read_bytes()
    if len(payload) != FLASH_SIZE:
        raise ValueError(
            f"expected {FLASH_SIZE} bytes of FlashRAM, found {len(payload)}"
        )
    if payload[VERSION_OFFSET:VERSION_OFFSET + len(VERSION)] != VERSION:
        raise ValueError("save version marker is missing or unsupported")
    if SAVE_DATA_SIZE > len(payload):
        raise ValueError("save payload is shorter than UnkBigBoy")

    reported: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    for slot, (pokemon_id, name) in enumerate(REPORT_SPECIES):
        score = struct.unpack_from(">i", payload, SCORE_TABLE_OFFSET + slot * 4)[0]
        marker = struct.unpack_from(
            ">i",
            payload,
            PHOTO_TABLE_OFFSET + slot * PHOTO_SIZE + PHOTO_VALID_OFFSET,
        )[0]
        entry = {"id": pokemon_id, "name": name}
        if marker == -1:
            missing.append(entry)
        else:
            reported.append({**entry, "score": score})

    return {
        "path": str(path),
        "reported_count": len(reported),
        "total_score": sum(item["score"] for item in reported),
        "reported": reported,
        "missing_count": len(missing),
        "missing": missing,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("save", type=Path, help="131072-byte FlashRAM save")
    parser.add_argument("--json", action="store_true", help="emit JSON")
    args = parser.parse_args()

    try:
        result = inspect_save(args.save)
    except (OSError, ValueError) as error:
        parser.error(str(error))

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    print(
        f"reported={result['reported_count']}/{len(REPORT_SPECIES)} "
        f"score={result['total_score']} missing={result['missing_count']}"
    )
    print("reported: " + ", ".join(
        f"{item['name']} ({item['id']}, {item['score']})"
        for item in result["reported"]
    ))
    print("missing: " + ", ".join(
        f"{item['name']} ({item['id']})" for item in result["missing"]
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
