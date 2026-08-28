#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "recover-decomp-address-symbols.py"
SPEC = importlib.util.spec_from_file_location("recover_symbols", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def expect_failure(text: str) -> None:
    try:
        MODULE.recover(text)
    except ValueError:
        return
    raise AssertionError("unsafe linker recovery was accepted")


symbols = MODULE.recover(
    "undefined reference to `D_800E80D0_A0F660'\n"
    "undefined reference to `D_beach_80318F00'\n"
    "undefined reference to `D_F00800'\n"
)
assert symbols == {
    "D_800E80D0_A0F660": 0x800E80D0,
    "D_F00800": 0x00F00800,
    "D_beach_80318F00": 0x80318F00,
}
expect_failure("undefined reference to `mystery_symbol'\n")
expect_failure("ordinary compiler failure\n")

rendered = MODULE.render_linker_script(symbols)
assert "PROVIDE(D_800E80D0_A0F660 = 0x800E80D0);" in rendered
assert "PROVIDE(D_F00800 = 0x00F00800);" in rendered

ninja = (
    "rule ld\n  "
    + MODULE.LD_COMMAND
    + "-Map $mapfile -T $in -o $out\n"
)
patched = MODULE.inject_linker_script(ninja, "build/snappad_undefined_syms.ld")
assert "-T build/snappad_undefined_syms.ld -Map" in patched
assert MODULE.inject_linker_script(patched, "build/snappad_undefined_syms.ld") == patched

with tempfile.TemporaryDirectory() as tmp:
    path = Path(tmp) / "symbols.ld"
    path.write_text(rendered)
    assert path.stat().st_size > 0

print("decomp address-symbol recovery contract passed")
