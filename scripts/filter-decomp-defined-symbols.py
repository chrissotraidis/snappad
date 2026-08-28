#!/usr/bin/env python3
"""Stop generated absolute metadata from overriding compiled ELF symbols."""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path


ASSIGNMENT_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=")
ENCODED_ADDRESS_RE = re.compile(r"(?:^|_)([0-9A-F]{8})(?:_|$)")
# These suffixes name objects embedded after the address-named parent. Their
# compiled ELF definitions carry the real subobject offset, so collapsing them
# back to the address token corrupts otherwise-correct R_MIPS_32 relocations.
EMBEDDED_SUBOBJECT_RE = re.compile(r"(?:_hitbox_[0-9]+|_pal)$")


def parse_defined_symbols(nm_output: str) -> set[str]:
    symbols: set[str] = set()
    for line in nm_output.splitlines():
        fields = line.split()
        if len(fields) >= 2:
            symbols.add(fields[-1])
    return symbols


def parse_text_symbols(nm_output: str) -> set[str]:
    symbols: set[str] = set()
    for line in nm_output.splitlines():
        fields = line.split()
        if len(fields) >= 2 and fields[-2] in {"T", "t"}:
            symbols.add(fields[-1])
    return symbols


def filter_assignments(text: str, defined: set[str]) -> tuple[str, list[str]]:
    kept: list[str] = []
    removed: list[str] = []
    for line in text.splitlines(keepends=True):
        match = ASSIGNMENT_RE.match(line)
        if match and match.group(1) in defined:
            removed.append(match.group(1))
        else:
            kept.append(line)
    return "".join(kept), removed


def encoded_address(symbol: str) -> int | None:
    if EMBEDDED_SUBOBJECT_RE.search(symbol):
        return None
    match = ENCODED_ADDRESS_RE.search(symbol)
    return int(match.group(1), 16) if match else None


def render_corrections(defined: set[str]) -> tuple[str, int]:
    corrections = sorted(
        (symbol, address)
        for symbol in defined
        if (address := encoded_address(symbol)) is not None
    )
    lines = [
        "/* Prefer the address explicitly encoded by decomp symbol names. */",
        "/* The exact-ROM checksum remains the authority for these corrections. */",
    ]
    lines.extend(f"{symbol} = 0x{address:08X};" for symbol, address in corrections)
    return "\n".join(lines) + "\n", len(corrections)


def inject_filtered_script(
    ninja_text: str, original: str, replacement: str
) -> str:
    old = f"-T {original} "
    new = f"-T {replacement} "
    if new in ninja_text:
        return ninja_text
    if ninja_text.count(old) != 1:
        raise ValueError("could not identify the unique generated-symbol linker input")
    return ninja_text.replace(old, new, 1)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--nm", type=Path, required=True)
    parser.add_argument("--objects", type=Path, required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--corrections", type=Path, required=True)
    parser.add_argument("--build-ninja", type=Path, required=True)
    args = parser.parse_args()

    objects = sorted(args.objects.rglob("*.o"))
    if not objects:
        raise SystemExit("error: decomp object directory contains no objects")
    result = subprocess.run(
        [str(args.nm), "-g", "--defined-only", *map(str, objects)],
        check=True,
        capture_output=True,
        text=True,
    )
    defined = parse_defined_symbols(result.stdout)
    text_symbols = parse_text_symbols(result.stdout)
    filtered, removed = filter_assignments(args.input.read_text(), defined)
    if not removed:
        raise SystemExit("error: no generated assignments overlap compiled definitions")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(filtered)
    # Direct linker assignments turn symbols absolute. That is tolerable for
    # corrected data addresses but destroys executable section ownership that
    # N64Recomp requires, so text symbols always retain their object metadata.
    correction_text, correction_count = render_corrections(defined - text_symbols)
    args.corrections.parent.mkdir(parents=True, exist_ok=True)
    args.corrections.write_text(correction_text)

    replacement = args.output.relative_to(args.build_ninja.parent).as_posix()
    corrections = args.corrections.relative_to(args.build_ninja.parent).as_posix()
    ninja_text = inject_filtered_script(
        args.build_ninja.read_text(), args.input.as_posix(), replacement
    )
    marker = f"-T {replacement} "
    corrected_marker = marker + f"-T {corrections} "
    if corrected_marker not in ninja_text:
        if ninja_text.count(marker) != 1:
            raise ValueError("could not identify the filtered linker input")
        ninja_text = ninja_text.replace(marker, corrected_marker, 1)
    args.build_ninja.write_text(ninja_text)
    print(
        f"Preferred {len(removed)} compiled definitions and corrected "
        f"{correction_count} address-encoded symbols."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
