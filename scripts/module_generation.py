"""Portable host tools and evidence-preserving generation for SnapPad."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from module_contract import ROOT, same_source_bytes, verify_generated, verify_source


def load_script(name, **paths):
    spec = importlib.util.spec_from_file_location("snappad_" + name.replace("-", "_"), ROOT / "scripts" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for key, value in paths.items():
        setattr(module, key, value)
    return module


def verify_decomp_stage(source, stage):
    """Bind an exported build stage to its exact, unchanged public source pin."""
    source = verify_source(source, "pokemonSnap", ())
    stage = Path(stage).resolve()
    env = dict(os.environ, GIT_OPTIONAL_LOCKS="0")
    names = subprocess.check_output(["git", "-C", str(source), "ls-tree", "-r", "--name-only", "-z", "HEAD"], env=env)
    names = set(names.decode().split("\0")) - {""}
    hashes = {}
    for name in sorted(names):
        original, exported = source / name, stage / name
        if (original.is_symlink() or exported.is_symlink() or not exported.is_file()
                or not same_source_bytes(exported.read_bytes(), original.read_bytes())):
            raise ValueError(f"Preserving changed or missing exported source: {exported}")
        hashes[name] = hashlib.sha256(exported.read_bytes()).hexdigest()
    # These are the trees scanned/imported by the generation helpers. A build
    # may add assets and objects elsewhere, but extra source here is unreviewed.
    for folder, suffix in (("src", ".c"), ("tools", ".py")):
        actual = {path.relative_to(stage).as_posix() for path in (stage / folder).rglob("*" + suffix)}
        expected = {name for name in names if name.startswith(folder + "/") and name.endswith(suffix)}
        if actual != expected:
            raise ValueError(f"Preserving unexpected source files in exported {folder}")
    return hashes


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_text_files(paths):
    for path in paths:
        data = path.read_bytes()
        if b"\0" in data:
            raise ValueError(f"Expected generated text, found binary data: {path}")
        normalized = data.replace(b"\r\n", b"\n")
        if normalized != data:
            path.write_bytes(normalized)


def rebuild_inputs(stage, rom):
    paths = [rom, stage / "build/pokemonsnap.z64", stage / "build/pokemonsnap.elf",
             stage / "build/pokemonsnap.map", *sorted((stage / "build").rglob("*.o"))]
    return {str(path): sha256(path) for path in paths}


def generate(source, stage, output, host_tools, readelf, objdump, normalized_rom):
    """Generate a new private G2 folder; original sources and rebuild stay read-only."""
    source, stage, output = Path(source).resolve(), Path(stage).resolve(), Path(output).resolve()
    if any(output == path or path in output.parents for path in (source, stage)):
        raise ValueError("Keep generated output outside the read-only source and rebuild stage")
    public_inputs = verify_decomp_stage(source, stage)
    rom, rebuilt = Path(normalized_rom).resolve(), stage / "build/pokemonsnap.z64"
    elf, linker_map = stage / "build/pokemonsnap.elf", stage / "build/pokemonsnap.map"
    # G1 itself checks the exact ROM. These hashes also bind every object read
    # for address-derived function sizes, and detect concurrent input changes.
    before = rebuild_inputs(stage, rom)
    output.mkdir(parents=True, exist_ok=False)
    aot, evidence, inventory = output / "aot", output / "evidence", output / "inventory"
    logs = output / "logs"; logs.mkdir()
    config = load_script("generate-n64recomp-config", DECOMP=stage, ELF=elf, MAP=linker_map,
        ROM=rom, SPLAT=stage / "splat.yaml", READELF=Path(readelf), OBJDUMP=Path(objdump),
        EVIDENCE=evidence / "G1.json", OUT=aot / "snappad-us.toml",
        METADATA_OUT=aot / "snappad_game_metadata.h", OUTPUT_FUNCS=aot / "snappad_recomp_out")
    g1 = load_script("record-g1-evidence")
    g1.record(rom, rebuilt, source, evidence / "G1.json", Path(host_tools["snappad_rom_xxh3"]), config)
    layout = load_script("inventory-source-layout", DECOMP=stage, SPLAT=stage / "splat.yaml",
                         LOAD_SOURCE=stage / "src/app_render/46270.c", OUT=inventory / "source-layout.json")
    layout.main(source_reference=source)
    config.main()
    dynamic = load_script("audit-dynamic-code", DECOMP=stage, ROM=rom, SPLAT=stage / "splat.yaml",
        G1_EVIDENCE=evidence / "G1.json", OBJDUMP=Path(objdump),
        PAYLOAD_OUT=aot / "dynamic/unk_segment_AA18E0_vpk0.bin",
        DISASSEMBLY_OUT=aot / "dynamic/unk_segment_AA18E0_vpk0.s",
        EVIDENCE_OUT=evidence / "G2-dynamic-code.json", CALLER=stage / "src/app_level/504770.c")
    dynamic.main()
    load_script("finalize-rsp-inventory", SOURCE_INVENTORY=inventory / "source-layout.json",
                ROM=rebuilt, OUT=inventory / "rsp-verified.json").main()
    load_script("generate-rsp-config", ROM=rebuilt, SPLAT=stage / "splat.yaml",
        RSP_INVENTORY=inventory / "rsp-verified.json", G1_EVIDENCE=evidence / "G1.json",
        OUT=aot / "snappad-audio-rsp.toml", RSP_OUTPUT=aot / "rsp/aspMain.cpp").main()
    (aot / "snappad_recomp_out").mkdir(exist_ok=True)
    (aot / "rsp").mkdir(exist_ok=True)
    for tool, name, log in (("N64Recomp", "snappad-us.toml", "n64recomp-generate.log"),
                            ("RSPRecomp", "snappad-audio-rsp.toml", "rsprecomp-audio-generate.log")):
        with (logs / log).open("wb") as stream:
            subprocess.run([str(host_tools[tool]), str(aot / name)], cwd=output, check=True,
                           stdout=stream, stderr=subprocess.STDOUT)
    normalize_text_files(path for path in aot.rglob("*") if path.suffix in (".c", ".cpp", ".h", ".inl", ".toml"))
    load_script("audit-generation-logs", N64_LOG=logs / "n64recomp-generate.log",
        RSP_LOG=logs / "rsprecomp-audio-generate.log", CPU_OUTPUT=aot / "snappad_recomp_out",
        RSP_OUTPUT=aot / "rsp/aspMain.cpp", N64_CONFIG=aot / "snappad-us.toml",
        RSP_CONFIG=aot / "snappad-audio-rsp.toml", METADATA=aot / "snappad_game_metadata.h",
        G1_EVIDENCE=evidence / "G1.json", DYNAMIC_CODE_EVIDENCE=evidence / "G2-dynamic-code.json",
        OUT=evidence / "G2-generation.json").main()
    if before != rebuild_inputs(stage, rom) or public_inputs != verify_decomp_stage(source, stage):
        raise ValueError("Source or private rebuild changed during generation; preserving outputs for diagnosis")
    verify_generated(output)
    (output / "generation-inputs.json").write_text(json.dumps({"public": public_inputs, "private": before}, indent=2) + "\n")
    return output


def generator_environment():
    env = dict(os.environ)
    if os.name != "nt" or shutil.which("cl", path=env.get("PATH")):
        return env
    installer = Path(env.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Microsoft Visual Studio/Installer/vswhere.exe"
    if not installer.is_file():
        raise ValueError("Install Visual Studio Build Tools with Desktop development with C++ and a Windows SDK, then try again.")
    native_arm64 = platform.machine().lower() in ("arm64", "aarch64")
    requirements = ["-requires", "Microsoft.VisualStudio.Component.VC.Tools.x86.x64"]
    if native_arm64:
        requirements = ["-requiresAny", *requirements, "Microsoft.VisualStudio.Component.VC.Tools.ARM64"]
    installation = subprocess.check_output([str(installer), "-latest", "-products", "*", *requirements,
                                            "-property", "installationPath", "-utf8"],
                                           text=True, encoding="utf-8").strip()
    versions = sorted((Path(installation) / "VC/Tools/MSVC").glob("*"), reverse=True)
    arm = native_arm64 and any(
        (version / "bin/Hostarm64/arm64/cl.exe").is_file() for version in versions)
    arch = "arm64" if arm else "x64"
    if not any((version / f"bin/Host{arch}/{arch}/cl.exe").is_file() for version in versions):
        raise ValueError(f"Visual Studio is missing its {arch} C++ compiler; add Desktop development with C++ and a Windows SDK.")
    script = Path(installation) / "VC/Auxiliary/Build/vcvarsall.bat"
    # cmd's default `set` output loses non-ANSI characters in inherited paths.
    command = subprocess.list2cmdline([env.get("COMSPEC", "cmd.exe")]) + f' /u /d /s /c ""{script}" {arch} >nul && set"'
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-16le", check=True, env=env)
    for line in result.stdout.splitlines():
        key, separator, value = line.partition("=")
        if separator and key:
            existing = next((name for name in env if name.casefold() == key.casefold()), key)
            env[existing] = value
    if not shutil.which("cl", path=env.get("Path", env.get("PATH"))):
        raise ValueError("Visual Studio could not prepare its C++ compiler. Check the Windows SDK components.")
    return env


def build_host_tools(source, build, jobs=2, env=None):
    if jobs < 1:
        raise ValueError("--jobs must be positive")
    source = verify_source(source)
    build = Path(build).resolve()
    build.mkdir(parents=True, exist_ok=True)
    env = generator_environment() if env is None else dict(env)
    cmake = shutil.which("cmake", path=env.get("PATH", env.get("Path")))
    if not cmake:
        raise ValueError("CMake is missing; use the tools supplied by PadMint")
    subprocess.run([cmake, "--fresh", "-S", str(ROOT / "cmake/host-tools"), "-B", str(build), "-G", "Ninja",
                    "-DCMAKE_BUILD_TYPE=Release", f"-DPython3_EXECUTABLE={sys.executable}",
                    f"-DSNAPPAD_RECUT_ROOT={source}"], cwd=build, env=env, check=True)
    subprocess.run([cmake, "--build", str(build), "--parallel", str(jobs), "--target",
                    "N64RecompCLI", "RSPRecomp", "snappad_rom_xxh3"], cwd=build, env=env, check=True)
    verify_source(source)
    suffix = ".exe" if os.name == "nt" else ""
    result = {name: build / (name + suffix) for name in ("N64Recomp", "RSPRecomp", "snappad_rom_xxh3")}
    if not all(path.is_file() for path in result.values()):
        raise ValueError("The native host build did not produce every required tool")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    verify = commands.add_parser("verify-source")
    verify.add_argument("source", type=Path)
    host = commands.add_parser("host-tools")
    host.add_argument("--source", type=Path, required=True)
    host.add_argument("--build", type=Path, required=True)
    host.add_argument("--jobs", type=int, default=2)
    generation = commands.add_parser("generate")
    generation.add_argument("--source", type=Path, required=True, help="Exact, clean decomp source checkout")
    generation.add_argument("--stage", type=Path, required=True, help="Exported source plus completed exact rebuild")
    generation.add_argument("--output", type=Path, required=True, help="New private G2 output folder")
    generation.add_argument("--host-tools", type=Path, required=True)
    generation.add_argument("--readelf", type=Path, required=True)
    generation.add_argument("--objdump", type=Path, required=True)
    generation.add_argument("--rom", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "verify-source":
        verify_source(args.source)
    elif args.command == "host-tools":
        print(json.dumps({key: str(value) for key, value in build_host_tools(args.source, args.build, args.jobs).items()}, indent=2))
    else:
        suffix = ".exe" if os.name == "nt" else ""
        hosts = {name: args.host_tools.resolve() / (name + suffix) for name in ("N64Recomp", "RSPRecomp", "snappad_rom_xxh3")}
        print(generate(args.source, args.stage, args.output, hosts, args.readelf.resolve(), args.objdump.resolve(), args.rom))


if __name__ == "__main__":
    main()
