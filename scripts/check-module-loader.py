#!/usr/bin/env python3
"""Exercise the actual module loader on a Mac using only hand-authored fixtures."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MODULE = r'''
#include "game_module.h"
extern "C" void synthetic_host_callback();
static void entry(uint8_t* bytes, recomp_context*) { bytes[0] = 7; }
static RspExitReason audio(uint8_t*, uint32_t n) { return static_cast<RspExitReason>(n); }
static void overlays() { synthetic_host_callback(); }
extern "C" int SnapPad_ConsumeTunnelHiddenPathReady() { return 1; }
extern "C" int SnapPad_IsFinalTunnelElectrodeFocused() { return 2; }
extern "C" int SnapPad_CurrentFocusedSubject() { return 3; }
extern "C" int SnapPad_ConsumeItemImpactSubject() { return 4; }
extern "C" __attribute__((visibility("default")))
const SnapPadGameModule* snappad_get_game_module() {
    static SnapPadGameModule table{snappad_game_module_version, sizeof(SnapPadGameModule),
        "synthetic-contract", 10, 123, "synthetic", u8"synthetic.game",
        entry, audio, overlays, SnapPad_ConsumeTunnelHiddenPathReady,
        SnapPad_IsFinalTunnelElectrodeFocused, SnapPad_CurrentFocusedSubject,
        SnapPad_ConsumeItemImpactSubject};
    /*MUTATE*/
    return &table;
}
'''
MAIN = r'''
#include "game_module.h"
#include "snappad_game_hooks.h"
#include "register_overlays.h"
#include <cstdio>
#include <cstring>
extern "C" void recomp_entrypoint(uint8_t*, recomp_context*);
RspExitReason aspMain(uint8_t*, uint32_t);
static int calls;
extern "C" __attribute__((visibility("default"))) void synthetic_host_callback() { ++calls; }
int main(int argc, char** argv) {
    if (snappad_game_module()) return 10;
    if (argc == 3) {
        if (!snappad_load_game_module(argv[1]) || snappad_game_module()) return 11;
        ++argv; --argc;
    }
    const char* error = snappad_load_game_module(argc > 1 ? argv[1] : nullptr);
    if (error) { std::puts(error); return 2; }
    const auto* value = snappad_game_module();
    if (!value || value->rom_xxh3 != 10 || value->entrypoint_address != 123 ||
        std::strcmp(value->internal_name, "synthetic") || std::u8string_view(value->game_id) != u8"synthetic.game") return 12;
    uint8_t bytes[1] = {0}; recomp_context context{};
    recomp_entrypoint(bytes, &context);
    if (bytes[0] != 7 || static_cast<int>(aspMain(bytes, 3)) != 3) return 13;
    pokemon_snap::register_overlays();
    if (calls != 1 || SnapPad_ConsumeTunnelHiddenPathReady() != 1 ||
        SnapPad_IsFinalTunnelElectrodeFocused() != 2 || SnapPad_CurrentFocusedSubject() != 3 ||
        SnapPad_ConsumeItemImpactSubject() != 4) return 14;
    if (snappad_load_game_module("missing-after-success")) return 15;
}
'''.replace('#include <cstring>', '#include <cstring>\n#include <string_view>')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-root", type=Path,
                        default=ROOT / "ref/paper-mario-recut/lib/N64ModernRuntime")
    args = parser.parse_args()
    includes = [ROOT / "port/runtime", args.runtime_root / "N64Recomp/include"]
    flags = ["xcrun", "clang++", "-std=c++20", '-DSNAPPAD_MODULE_ID="synthetic-contract"',
             *["-I" + str(path) for path in includes]]
    cases = {
        "good": "", "wrong_version": "table.version = 99;", "wrong_size": "table.size = 0;",
        "wrong_identity": 'table.identity = "different-build";', "null_identity": "table.identity = nullptr;",
        "zero_rom": "table.rom_xxh3 = 0;", "zero_entry_address": "table.entrypoint_address = 0;",
        "null_internal_name": "table.internal_name = nullptr;", "null_game_id": "table.game_id = nullptr;",
        "null_entry": "table.entrypoint = nullptr;", "null_audio": "table.audio = nullptr;",
        "null_overlays": "table.register_overlays = nullptr;",
        "null_tunnel": "table.consume_tunnel_hidden_path_ready = nullptr;",
        "null_electrode": "table.is_final_tunnel_electrode_focused = nullptr;",
        "null_focus": "table.current_focused_subject = nullptr;",
        "null_impact": "table.consume_item_impact_subject = nullptr;", "null_table": "return nullptr;",
    }
    results = {}
    with tempfile.TemporaryDirectory(prefix="SnapPad loader spaces ") as temporary:
        work = Path(temporary)
        (work / "main.cpp").write_text(MAIN)
        subprocess.run([*flags, ROOT / "port/runtime/game_module_loader.cpp", work / "main.cpp",
                        "-Wl,-export_dynamic", "-o", work / "loader"], check=True)
        for name, mutation in {**cases, "no_getter": ""}.items():
            source = work / (name + ".cpp")
            source.write_text(MODULE.replace("/*MUTATE*/", mutation) if name != "no_getter" else "int unused;\n")
            subprocess.run([*flags, "-fvisibility=hidden", "-dynamiclib", "-Wl,-undefined,dynamic_lookup",
                            source, "-o", work / (name + ".dylib")], check=True)
        for name in [*cases, "no_getter", "missing"]:
            result = subprocess.run([work / "loader", work / (name + ".dylib")], capture_output=True, text=True)
            expected = 0 if name == "good" else 2
            if result.returncode != expected:
                raise RuntimeError(f"{name}: {result.returncode}: {result.stdout} {result.stderr}")
            results[name] = result.returncode
        result = subprocess.run([work / "loader", work / "wrong_identity.dylib", work / "good.dylib"],
                                capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError("Loading a matching module after rejection failed")
        results["retry_after_rejection"] = 0
        names = subprocess.check_output(["xcrun", "nm", "-gUj", work / "good.dylib"], text=True).splitlines()
        if names != ["_snappad_get_game_module"]:
            raise RuntimeError(f"Unexpected private module exports: {names}")
    evidence = ROOT / "build/module-evidence"
    evidence.mkdir(parents=True, exist_ok=True)
    report = {"synthetic_native_mac_abi": results, "ios_loading": "not-tested", "gameplay": "not-tested"}
    (evidence / "loader-abi.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
