#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path, PureWindowsPath
import subprocess
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "filter-decomp-defined-symbols.py"
SPEC = importlib.util.spec_from_file_location("filter_symbols", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

defined = MODULE.parse_defined_symbols(
    "object.o: 00000000 T send_mesg\nobject.o: 00000010 D gState\n"
)
assert defined == {"send_mesg", "gState"}
assert MODULE.parse_text_symbols(
    "object.o: 00000000 T func_80000400\nobject.o: 00000010 D gState\n"
) == {"func_80000400"}

filtered, removed = MODULE.filter_assignments(
    "send_mesg = 0x800337E4;\nabsolute_only = 0x80000000;\ngState = 0x80040000;\n",
    defined,
)
assert removed == ["send_mesg", "gState"]
assert filtered == "absolute_only = 0x80000000;\n"

assert MODULE.encoded_address("D_801F70A0_9A6B10") == 0x801F70A0
assert MODULE.encoded_address("D_camera_check_802499B0") == 0x802499B0
assert MODULE.encoded_address("send_mesg") is None
assert MODULE.encoded_address("D_8011CF54_hitbox_0") is None
assert MODULE.encoded_address("magmar_hd_tex_801A9930_pal") is None
assert MODULE.encoded_address("magmar_hd_tex_801A9930_png") == 0x801A9930
corrections, count = MODULE.render_corrections(
    {"D_801F70A0_9A6B10", "D_camera_check_802499B0", "send_mesg"}
)
assert count == 2
assert "D_801F70A0_9A6B10 = 0x801F70A0;" in corrections
assert "D_camera_check_802499B0 = 0x802499B0;" in corrections

ninja = "command = mips-linux-gnu-ld -T undefined_syms_auto.txt -Map out.map\n"
patched = MODULE.inject_filtered_script(
    ninja, "undefined_syms_auto.txt", "build/filtered.txt"
)
assert "-T build/filtered.txt -Map" in patched
assert MODULE.inject_filtered_script(
    patched, "undefined_syms_auto.txt", "build/filtered.txt"
) == patched

# A real decomp's hundreds of absolute Windows object paths exceed CreateProcess.
# Exercise the complete collector with spaced and non-BMP paths and check that
# every definition survives, including the final short batch.
objects = [PureWindowsPath("V:/work with spaces/\U0001f9ea/" + "nested/" * 20 + f"file{i}.o")
           for i in range(1200)]
visited = []
def fake_nm(command, **kwargs):
    assert len(subprocess.list2cmdline(command).encode("utf-16-le")) // 2 + 1 <= 16000
    assert kwargs["check"] and kwargs["capture_output"] and kwargs["text"]
    visited.extend(command[3:])
    lines = []
    for item in command[3:]:
        stem = PureWindowsPath(item).stem
        lines.extend((f"00000000 T code_{stem}", f"00000004 D data_{stem}"))
    return subprocess.CompletedProcess(command, 0, "\n".join(lines), "")

with mock.patch.object(MODULE.subprocess, "run", side_effect=fake_nm) as run:
    all_defined, all_text = MODULE.collect_defined_symbols(Path("nm tool"), objects)
    assert run.call_count > 1
assert visited == list(map(str, objects))
assert all_text == {f"code_file{i}" for i in range(1200)}
assert all_defined == all_text | {f"data_file{i}" for i in range(1200)}
with mock.patch.object(MODULE.subprocess, "run", side_effect=subprocess.CalledProcessError(2, "nm")):
    try:
        MODULE.collect_defined_symbols(Path("nm"), [Path("object.o")])
    except subprocess.CalledProcessError:
        pass
    else:
        raise AssertionError("nm failure was ignored")

print("decomp defined-symbol filtering contract passed")
