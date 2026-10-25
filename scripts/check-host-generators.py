#!/usr/bin/env python3
"""Exercise pinned native generators with public hand-authored inputs only."""
import argparse
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))
from module_generation import build_host_tools, generator_environment
from module_contract import verify_source


def check(binary, source, env):
    suffix = ".exe" if os.name == "nt" else ""
    with tempfile.TemporaryDirectory(prefix="Snap synthetic generator 雪 spaces ") as temporary:
        work = Path(temporary)
        if os.name == "nt":
            mt = shutil.which("mt", path=env.get("Path", env.get("PATH")))
            if not mt:
                raise RuntimeError("Visual Studio did not provide the manifest inspection tool")
            for name in ("N64Recomp", "RSPRecomp", "snappad_rom_xxh3"):
                manifest = work / (name + ".manifest")
                subprocess.run([mt, "-nologo", "-inputresource:" + str(binary / (name + suffix)) + ";#1",
                                "-out:" + str(manifest)], env=env, capture_output=True, check=True)
                tree = ET.parse(manifest)
                codepage = tree.find(".//{http://schemas.microsoft.com/SMI/2019/WindowsSettings}activeCodePage")
                execution = tree.find(".//{urn:schemas-microsoft-com:asm.v3}requestedExecutionLevel")
                if codepage is None or codepage.text != "UTF-8" or execution is None or execution.get("level") != "asInvoker":
                    raise RuntimeError("Host generator lost UTF-8 paths or ordinary execution privileges")
        # addiu v0,zero,7; jr ra; addiu v0,v0,1 (the delay slot must run).
        (work / "cpu 雪.bin").write_bytes(bytes(0x1000) + struct.pack(">3I", 0x24020007, 0x03E00008, 0x24420001))
        (work / "symbols 雪.toml").write_text('''[[section]]
name = ".text"
rom = 0x1000
vram = 0x80001000
size = 12
functions = [{ name = "recomp_entrypoint", vram = 0x80001000, rom = 0x1000, size = 12 }]
''', encoding="utf-8")
        (work / "cpu 雪.toml").write_text('''[input]
entrypoint = 0x80001000
symbols_file_path = "symbols 雪.toml"
rom_file_path = "cpu 雪.bin"
output_func_path = "output 雪"
''', encoding="utf-8")
        subprocess.run([binary / ("N64Recomp" + suffix), work / "cpu 雪.toml"], cwd=work, check=True)
        generated = sorted((work / "output 雪").glob("funcs_*.c"))
        if len(generated) != 1:
            raise RuntimeError("The synthetic CPU input did not produce one function file")
        (work / "main.c").write_text('''#include "recomp.h"
void recomp_entrypoint(uint8_t*, recomp_context*);
int main(void) {
    uint8_t rdram[8] = {0}; recomp_context ctx = {0};
    recomp_entrypoint(rdram, &ctx);
    return ctx.r2 == 8 ? 0 : 1;
}
''')
        include = source / "lib/N64ModernRuntime/N64Recomp/include"
        executable = work / ("cpu-test" + suffix)
        if os.name == "nt":
            compiler = shutil.which("cl", path=env.get("Path", env.get("PATH")))
            if not compiler:
                raise RuntimeError("Visual Studio did not provide a C compiler")
            command = [compiler, "/nologo", "/TC", "/std:c11", "/I" + str(include),
                       *generated, work / "main.c", "/Fe:" + str(executable)]
        else:
            command = ["cc", "-std=c11", "-I" + str(include), *generated, work / "main.c", "-o", executable]
        subprocess.run([str(arg) for arg in command], cwd=work, env=env, check=True)
        subprocess.run([executable], cwd=work, check=True)

        # Independent RSP BREAK instructions and deliberately unsorted dispatch targets.
        (work / "rsp 雪.bin").write_bytes(struct.pack(">3I", 0x0000000D, 0x0000000D, 0x0000000D))
        (work / "rsp 雪.toml").write_text('''text_offset = 0
text_size = 12
text_address = 0x04001000
rom_file_path = "rsp 雪.bin"
output_file_path = "rsp 雪.cpp"
output_function_name = "synthetic_audio"
extra_indirect_branch_targets = [0x1008, 0x1000, 0x1004]
''', encoding="utf-8")
        subprocess.run([binary / ("RSPRecomp" + suffix), work / "rsp 雪.toml"], cwd=work, check=True)
        output = (work / "rsp 雪.cpp").read_text()
        targets = re.findall(r"case 0x([0-9A-Fa-f]+): goto L_", output)
        if targets != ["1000", "1004", "1008"] or "RspExitReason::Broke" not in output:
            raise RuntimeError("The synthetic RSP dispatch or BREAK output changed")
        # This vector is published in the pinned xxHash sanity test data.
        empty = work / "empty 雪.bin"; empty.write_bytes(b"")
        digest = subprocess.check_output([binary / ("snappad_rom_xxh3" + suffix), empty], text=True).strip()
        if digest != "0x2D06800538D394C2":
            raise RuntimeError("The native ROM hash helper failed the upstream empty-input vector")
    print("Synthetic CPU execution, ordered RSP dispatch and XXH3 vector passed with Unicode paths.", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--bin", type=Path, help="Reuse already-built generator executables")
    parser.add_argument("--build", type=Path, help="Build native tools in this separate folder")
    parser.add_argument("--jobs", type=int, default=2)
    args = parser.parse_args()
    if bool(args.bin) == bool(args.build):
        parser.error("Choose exactly one of --bin or --build")
    source = verify_source(args.source)
    env = generator_environment()
    if args.build:
        tools = build_host_tools(source, args.build, args.jobs, env)
        binary = tools["N64Recomp"].parent
    else:
        binary = args.bin.resolve()
    check(binary, source, env)


if __name__ == "__main__":
    main()
