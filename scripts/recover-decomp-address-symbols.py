#!/usr/bin/env python3
"""Recover address-named symbols omitted by the pinned decomp link metadata.

This is deliberately narrow: it only accepts symbols whose address is encoded
in the established Pokemon Snap decomp name, plus one audited literal alias.
The final ROM checksum remains the authority on whether the recovery is exact.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path


UNDEFINED_RE = re.compile(r"undefined reference to [`']([^`']+)'?")
DIRECT_ADDRESS_RE = re.compile(r"^D_([0-9A-F]{8})(?:_[0-9A-F]+)?$")
SCOPED_ADDRESS_RE = re.compile(r"^D_[a-z][A-Za-z0-9_]*_([0-9A-F]{8})$")
AUDITED_ALIASES = {"D_F00800": 0x00F00800}
LD_COMMAND = (
    "command = mips-linux-gnu-ld -T undefined_syms.txt "
    "-T undefined_syms_auto.txt "
)


def symbol_address(symbol: str) -> int | None:
    for pattern in (DIRECT_ADDRESS_RE, SCOPED_ADDRESS_RE):
        match = pattern.fullmatch(symbol)
        if match:
            return int(match.group(1), 16)
    return AUDITED_ALIASES.get(symbol)


def recover(log_text: str) -> dict[str, int]:
    symbols = sorted(set(UNDEFINED_RE.findall(log_text)))
    if not symbols:
        raise ValueError("link log contains no undefined references")

    recovered: dict[str, int] = {}
    rejected: list[str] = []
    for symbol in symbols:
        address = symbol_address(symbol)
        if address is None:
            rejected.append(symbol)
        else:
            recovered[symbol] = address

    if rejected:
        raise ValueError(
            "refusing to infer symbols without an audited encoded address: "
            + ", ".join(rejected)
        )
    return recovered


def render_linker_script(symbols: dict[str, int]) -> str:
    lines = [
        "/* Generated from the pinned decomp linker's undefined references. */",
        "/* PROVIDE never overrides a definition supplied by an object file. */",
    ]
    lines.extend(
        f"PROVIDE({symbol} = 0x{address:08X});"
        for symbol, address in symbols.items()
    )
    return "\n".join(lines) + "\n"


def inject_linker_script(ninja_text: str, linker_script: str) -> str:
    replacement = LD_COMMAND + f"-T {linker_script} "
    if replacement in ninja_text:
        return ninja_text
    if ninja_text.count(LD_COMMAND) != 1:
        raise ValueError("could not identify the unique pinned decomp link rule")
    return ninja_text.replace(LD_COMMAND, replacement, 1)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--build-ninja", type=Path, required=True)
    args = parser.parse_args()

    symbols = recover(args.log.read_text(errors="replace"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_linker_script(symbols))

    ninja_text = args.build_ninja.read_text()
    linker_script = args.output.relative_to(args.build_ninja.parent).as_posix()
    args.build_ninja.write_text(inject_linker_script(ninja_text, linker_script))
    print(f"Recovered {len(symbols)} strictly address-backed linker symbols.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
