#!/usr/bin/env python3
"""Private Windows ROM-to-module build using an explicitly verified local tool bundle.

The candidate bundle is a maintainer input until its tools are approved for
distribution. This does not change the published Mac recipe or download tools.
"""
import argparse
import base64
import csv
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import sysconfig
import tarfile
import tempfile
import uuid
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import module_contract
import module_generation

ROOT = Path(__file__).resolve().parents[1]
ROLES = {"ido53", "ido71", "asm_processor", "as", "ld", "objcopy", "strip",
         "pigment64", "readelf", "objdump", "uv", "rabbitizer_wheel", "cpp",
         "setuptools_wheel", "wheel_wheel", "packaging_wheel"}
DECOMP_ROLES = {"ido53", "ido71", "asm_processor", "as", "ld", "objcopy", "strip", "pigment64"}
WHEEL_VERSION = "1.14.3+padmint.1"
BUILD_WHEELS = {"setuptools": "80.9.0", "wheel": "0.45.1", "packaging": "25.0"}


def sha256(path):
    return module_generation.sha256(path)


def digest_json(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def linked(path):
    return path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction())


def relative_file(root, name):
    relative = PurePosixPath(name)
    if not name or "\\" in name or relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"Invalid relative inventory path: {name}")
    path = root.joinpath(*relative.parts)
    cursor = path
    while cursor != root:
        if linked(cursor):
            raise ValueError(f"Linked inventory input is not supported: {path}")
        cursor = cursor.parent
        if cursor == cursor.parent:
            raise ValueError(f"Escaped inventory input: {path}")
    if not path.is_file() or root not in path.resolve().parents:
        raise ValueError(f"Missing or escaped inventory input: {path}")
    return path


def verified_tools(manifest, expected_sha256):
    manifest = Path(manifest).resolve()
    if sha256(manifest) != expected_sha256:
        raise ValueError("Local tool-bundle manifest checksum does not match the reviewed input")
    data = json.loads(manifest.read_text())
    if data.get("schema") != 1 or set(data.get("paths", {})) != ROLES:
        raise ValueError("Unsupported local tool-bundle schema or role set")
    if data.get("python") != {"abi": "cp313-win_amd64", "rabbitizer_version": WHEEL_VERSION}:
        raise ValueError("The local bundle must provide the reviewed CPython 3.13 x64 Rabbitizer wheel")
    paths = {}
    for name, value in data["paths"].items():
        path = Path(value)
        if not path.is_absolute() or linked(path):
            raise ValueError(f"Tool role must name an absolute, unlinked file: {name}")
        paths[name] = path.resolve()
    inventory = {}
    for component in data.get("components", []):
        root = Path(component["root"])
        receipt = Path(component["receipt"])
        if not root.is_absolute() or linked(root) or not root.is_dir():
            raise ValueError("Tool component root must be an existing unlinked absolute directory")
        root = root.resolve()
        if not receipt.is_absolute() or linked(receipt) or sha256(receipt) != component["receipt_sha256"]:
            raise ValueError(f"Tool provenance receipt changed: {receipt}")
        expected = set()
        for item in component["files"]:
            path = relative_file(root, item["path"])
            if item["path"] in expected or sha256(path) != item["sha256"]:
                raise ValueError(f"Duplicate or changed tool inventory file: {path}")
            expected.add(item["path"])
            if path in inventory and inventory[path] != item["sha256"]:
                raise ValueError(f"Conflicting tool inventory: {path}")
            inventory[path] = item["sha256"]
        if component.get("complete") is True:
            ido = component.get("kind") == "ido"
            roles = {name for name, path in paths.items() if root in path.parents}
            if ido and (not roles or not roles <= {"ido53", "ido71"}):
                raise ValueError("Only an IDO runtime root may exclude writable tmp files")
            actual = set()
            for path in root.rglob("*"):
                name = path.relative_to(root).as_posix()
                if linked(path):
                    raise ValueError(f"Linked tool inventory entry: {path}")
                if ido and (name == "tmp" or name.startswith("tmp/")):
                    if name == "tmp" and not path.is_dir():
                        raise ValueError("IDO tmp must be a normal directory")
                    continue
                if path.is_file():
                    actual.add(name)
            if expected != actual:
                raise ValueError(f"Tool component inventory changed: {root}")
    if not all(path in inventory for path in paths.values()):
        raise ValueError("Every tool role must be covered by the verified file inventory")
    with zipfile.ZipFile(paths["rabbitizer_wheel"]) as wheel:
        metadata = [name for name in wheel.namelist() if name.endswith(".dist-info/METADATA")]
        tags = [name for name in wheel.namelist() if name.endswith(".dist-info/WHEEL")]
        if (len(metadata) != 1 or len(tags) != 1
                or "Name: rabbitizer" not in wheel.read(metadata[0]).decode().splitlines()
                or f"Version: {WHEEL_VERSION}" not in wheel.read(metadata[0]).decode().splitlines()
                or "Tag: cp313-cp313-win_amd64" not in wheel.read(tags[0]).decode().splitlines()):
            raise ValueError("Unexpected Rabbitizer wheel distribution or Python ABI")
    for name, version in BUILD_WHEELS.items():
        with zipfile.ZipFile(paths[name + "_wheel"]) as wheel:
            # setuptools also ships vendored dependency metadata; only its
            # top-level distribution metadata identifies this wheel.
            metadata = [member for member in wheel.namelist()
                        if member.count("/") == 1 and member.endswith(".dist-info/METADATA")]
            if len(metadata) != 1 or not {f"Name: {name}", f"Version: {version}"}.issubset(wheel.read(metadata[0]).decode().splitlines()):
                raise ValueError(f"Unexpected frozen Python build prerequisite: {name}")
    return paths


def windows_environment():
    if os.name != "nt" or sys.version_info[:2] != (3, 13) or sysconfig.get_platform() != "win-amd64":
        raise ValueError("Use PadMint's bundled x64 CPython 3.13 on Windows for this candidate")
    env = module_generation.generator_environment()
    # vcvars selects the usable compiler architecture. Its SDK must contain
    # matching import libraries, including ARM64 when that compiler is selected.
    values = {key.casefold(): value for key, value in env.items()}
    arch = values.get("vscmd_arg_tgt_arch", "").lower()
    sdk, version = values.get("windowssdkdir"), values.get("windowssdkversion", "").strip("/\\")
    if arch not in ("x64", "arm64") or not sdk or not version:
        raise ValueError("Visual Studio must provide C++ tools and a Windows SDK for the selected host architecture")
    sdk = Path(sdk)
    for relative in (f"Include/{version}/um/Windows.h", f"Include/{version}/ucrt/stdio.h",
                     f"Lib/{version}/um/{arch}/kernel32.lib", f"Lib/{version}/ucrt/{arch}/ucrt.lib"):
        if not (sdk / relative).is_file():
            raise ValueError(f"Install the Windows SDK and {arch} C++ library components: missing {relative}")
    env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1", GIT_OPTIONAL_LOCKS="0")
    return env


def run(command, log, cwd, env):
    command = [str(value) for value in command]
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("ab") as stream:
        stream.write((repr(command) + "\n").encode())
        result = subprocess.run(command, cwd=cwd, env=env, stdout=stream, stderr=subprocess.STDOUT)
    if result.returncode:
        raise RuntimeError(f"Build command failed; preserving work and log: {log}")
    return result.returncode


def prepare_source(key, destination, env, cache=None):
    lock = json.loads((ROOT / "dependencies.lock.json").read_text())
    source = lock["sources"][key]
    patches = ("n64recomp", "n64modernruntime", "rt64") if key == "paperMarioReCut" else ()
    if destination.exists():
        return module_contract.verify_source(destination, key, patches)
    destination.parent.mkdir(parents=True, exist_ok=True)
    # An optional cache supplies Git objects only. Its worktree, private inputs
    # and index are never copied or changed.
    stage = Path(tempfile.mkdtemp(prefix=destination.name + "-preparing-", dir=destination.parent))
    log = stage / "prepare.log"
    fetch_env = dict(env, GIT_NO_LAZY_FETCH="1") if cache else env
    for arguments in (("init", "-q"), ("config", "core.autocrlf", "false"), ("config", "core.longpaths", "true"),
                      ("remote", "add", "origin", source["url"]),
                      ("fetch", "--depth=1", str(Path(cache).resolve()) if cache else "origin", source["commit"]),
                      ("checkout", "--detach", source["commit"]),
                      ("remote", "set-url", "--push", "origin", "DISABLED")):
        run(["git", *arguments], log, stage, fetch_env)
    log.rename(stage.parent / (stage.name + ".log"))
    for folder in patches:
        for patch in sorted((ROOT / "port/patches" / folder).glob("*.patch")):
            subprocess.run(["git", "apply", "-"], cwd=stage, env=env,
                           input=patch.read_bytes().replace(b"\r\n", b"\n"), check=True)
    module_contract.verify_source(stage, key, patches)
    stage.rename(destination)
    return destination


def source_destination(work, key):
    source = json.loads((ROOT / "dependencies.lock.json").read_text())["sources"][key]
    folders = ("n64recomp", "n64modernruntime", "rt64") if key == "paperMarioReCut" else ()
    patches = {path.relative_to(ROOT).as_posix(): sha256(path)
               for folder in folders for path in sorted((ROOT / "port/patches" / folder).glob("*.patch"))}
    identifier = digest_json({"source": source, "patches": patches})
    prefix = "r" if key == "paperMarioReCut" else "d"
    return work / "sources" / (prefix + "-" + identifier[:16])


def export_source(source, destination, env):
    destination.mkdir(parents=True, exist_ok=False)
    archive = destination.parent / (destination.name + ".tar")
    with archive.open("xb") as stream:
        subprocess.run(["git", "-C", str(source), "archive", "HEAD"], stdout=stream, env=env, check=True)
    with tarfile.open(archive) as members:
        for member in members:
            relative = PurePosixPath(member.name)
            if relative.is_absolute() or ".." in relative.parts or not (member.isdir() or member.isfile()):
                raise ValueError(f"Unsupported exported source member: {member.name}")
            target = destination.joinpath(*relative.parts)
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with members.extractfile(member) as incoming, target.open("xb") as outgoing:
                    shutil.copyfileobj(incoming, outgoing)
    archive.unlink()
    module_generation.verify_decomp_stage(source, destination)


def normalize_rom(source, destination, specification):
    if not source.is_file() or source.stat().st_size != specification["size"]:
        raise ValueError("The selected ROM has an unsupported size")
    data = source.read_bytes()
    if data[:4] == bytes.fromhex("37804012"):
        if len(data) % 2:
            raise ValueError("Odd-length v64 input")
        normalized = bytearray(data); normalized[0::2], normalized[1::2] = data[1::2], data[0::2]
        data = bytes(normalized)
    elif data[:4] == bytes.fromhex("40123780"):
        if len(data) % 4:
            raise ValueError("Non-word-aligned n64 input")
        data = b"".join(data[index:index + 4][::-1] for index in range(0, len(data), 4))
    elif data[:4] != bytes.fromhex("80371240"):
        raise ValueError("Unrecognized N64 ROM byte order")
    if hashlib.sha1(data).hexdigest() != specification["sha1"]:
        raise ValueError("The normalized ROM does not match the supported revision")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("xb") as stream:
        stream.write(data)
    return hashlib.sha256(data).hexdigest()


def installed_wheel(wheel_path, site_packages):
    """Check installed payload bytes and every installed RECORD entry."""
    files = {}
    with zipfile.ZipFile(wheel_path) as wheel:
        for name in wheel.namelist():
            if name.endswith("/") or name.endswith(".dist-info/RECORD"):
                continue
            path = relative_file(site_packages, name)
            expected = hashlib.sha256(wheel.read(name)).hexdigest()
            if sha256(path) != expected:
                raise ValueError(f"Installed wheel payload does not match the approved archive: {name}")
            files[path] = expected
        names = [name for name in wheel.namelist() if name.endswith(".dist-info/RECORD")]
    if len(names) != 1:
        raise ValueError("The approved wheel must contain exactly one RECORD")
    record = relative_file(site_packages, names[0])
    recorded = set()
    with record.open(newline="", encoding="utf-8") as stream:
        for name, checksum, size in csv.reader(stream):
            path = relative_file(site_packages, name)
            if path in recorded:
                raise ValueError("Duplicate installed wheel RECORD entry")
            recorded.add(path)
            if path == record and not checksum and not size:
                continue
            expected = "sha256=" + base64.urlsafe_b64encode(bytes.fromhex(sha256(path))).decode().rstrip("=")
            if checksum != expected or str(path.stat().st_size) != size:
                raise ValueError(f"Installed wheel RECORD does not match {name}")
            files[path] = sha256(path)
    if not set(files).issubset(recorded):
        raise ValueError("Installed wheel RECORD omits approved payload files")
    files[record] = sha256(record)
    return files


def python_environment(source, project, paths, env, log):
    project.mkdir(parents=True, exist_ok=False)
    for name in ("pyproject.toml", "uv.lock"):
        shutil.copyfile(source / name, project / name)
    child = dict(env, UV_CACHE_DIR=str(project.parent / "uv-cache"), UV_PYTHON_DOWNLOADS="never",
                 UV_LINK_MODE="copy", UV_PROJECT_ENVIRONMENT=str(project / ".venv"))
    # uv's Windows file-URL parser does not accept UNC authorities here. Keep
    # the three small, verified build wheels in this new local project.
    wheel_folder = project / "build-wheels"; wheel_folder.mkdir()
    requirements = []
    for name in BUILD_WHEELS:
        source = paths[name + "_wheel"]
        destination = wheel_folder / source.name
        shutil.copyfile(source, destination)
        if sha256(destination) != sha256(source):
            raise ValueError("Python build prerequisite changed during staging")
        requirements.append(name + " @ " + destination.as_uri())
    constraints = project / "build-constraints.toml"
    constraints.write_text("build-constraint-dependencies = " + json.dumps(requirements) + "\n")
    run([paths["uv"], "sync", "--project", project, "--frozen", "--no-dev", "--no-build-package", "rabbitizer",
         "--config-file", constraints,
         "--python", sys.executable, "--no-python-downloads"], log, project, child)
    python = project / ".venv/Scripts/python.exe"
    inventory = "import importlib.metadata as m,json;print(json.dumps({d.metadata['Name'].lower():d.version for d in m.distributions()},sort_keys=True))"
    before = json.loads(subprocess.check_output([python, "-B", "-c", inventory], env=child, text=True))
    if before.get("rabbitizer") != "1.14.3":
        raise ValueError("The frozen upstream Python lock no longer selects Rabbitizer 1.14.3")
    run([paths["uv"], "pip", "install", "--python", python, "--no-index", "--no-deps", paths["rabbitizer_wheel"]], log, project, child)
    after = json.loads(subprocess.check_output([python, "-B", "-c", inventory], env=child, text=True))
    expected = dict(before, rabbitizer=WHEEL_VERSION)
    if after != expected:
        raise ValueError("The isolated Python override changed more than the approved Rabbitizer wheel")
    (project / "distributions.json").write_text(json.dumps(after, indent=2) + "\n")
    # JSON escapes non-ASCII paths across different parent/child stdout encodings.
    site = Path(json.loads(subprocess.check_output([python, "-B", "-c",
        "import sysconfig,json;print(json.dumps(sysconfig.get_path('purelib')))"], env=child)))
    files = installed_wheel(paths["rabbitizer_wheel"], site)
    (project / "wheel-installed.json").write_text(json.dumps({str(path): value for path, value in files.items()}, indent=2) + "\n")
    return python, files


def saved_result(work, key):
    record = work / "complete.json"
    if not record.exists():
        return None
    try:
        value = json.loads(record.read_text())
        if value.get("schema") != 1 or value.get("key") != key:
            return None
        files = value["files"]
        if not files or value["module"] not in files:
            return None
        for name, checksum in files.items():
            if sha256(relative_file(work, name)) != checksum:
                return None
        return relative_file(work, value["module"])
    except (OSError, ValueError, KeyError, TypeError):
        return None


def write_result(module, work, result):
    value = {"file": module.relative_to(work).as_posix(), "into": "Frameworks/SnapPadGame.dylib", "sha256": sha256(module)}
    result.parent.mkdir(parents=True, exist_ok=True)
    temporary = result.with_name(result.name + "." + uuid.uuid4().hex + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    os.replace(temporary, result)


def validate_output_paths(work, result, inputs):
    if result.parent.resolve() != work or result.suffix != ".json" or result.name == "complete.json" or linked(result):
        raise ValueError("Write the module result as a separate JSON file directly inside the work folder")
    outputs = {result.resolve(), work / "complete.json"}
    if any(Path(path).resolve() in outputs for path in inputs):
        raise ValueError("The result and cache record must not replace an input file")


def build_key(rom_hash, tools_hash, toolchain):
    sdk = {}
    for path in sorted(toolchain.parent.rglob("*")):
        if linked(path):
            raise ValueError(f"Linked prepared SDK input: {path}")
        if path.is_file():
            sdk[path.relative_to(toolchain.parent).as_posix()] = sha256(path)
    return digest_json({"rom": rom_hash, "tools": tools_hash, "contract": module_contract.identity(),
        "sdk": sdk, "python": sys.version,
        "scripts": {path.name: sha256(path) for path in sorted((ROOT / "scripts").glob("*.py"))}})


def build(args):
    env = windows_environment()
    env.update(PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    paths = verified_tools(args.tools, args.tools_sha256)
    work = args.work.resolve(); work.mkdir(parents=True, exist_ok=True)
    result = args.result.absolute()
    validate_output_paths(work, result, (args.rom, args.tools, args.toolchain))
    toolchain = args.toolchain.resolve()
    if not toolchain.is_file():
        raise ValueError("PadMint's prepared iOS toolchain is missing")
    for required in ("git", "cmake", "ninja"):
        if not shutil.which(required, path=env.get("PATH", env.get("Path"))):
            raise ValueError(f"Missing {required}; use the tools supplied by PadMint")
    lock = json.loads((ROOT / "dependencies.lock.json").read_text())
    original = args.rom.resolve()
    original_hash = sha256(original)
    key = build_key(original_hash, args.tools_sha256, toolchain)
    cached = saved_result(work, key)
    if cached:
        print("Verified complete private build cache.", flush=True)
        write_result(cached, work, result); return cached
    attempt = Path(tempfile.mkdtemp(prefix="attempt-", dir=work))
    logs = attempt / "logs"
    normalized = attempt / "pokemonsnap.z64"
    normalize_rom(original, normalized, lock["rom"])
    decomp = prepare_source("pokemonSnap", source_destination(work, "pokemonSnap"), env, args.decomp_cache)
    recut = prepare_source("paperMarioReCut", source_destination(work, "paperMarioReCut"), env, args.recut_cache)
    stage = attempt / "decomp"
    export_source(decomp, stage, env)
    shutil.copyfile(normalized, stage / "pokemonsnap.z64")
    python, installed = python_environment(decomp, attempt / "python", paths, env, logs / "python.log")
    configuration = {key: str(paths[key]) for key in DECOMP_ROLES}
    configuration["cpp"] = [str(paths["cpp"]), "-E", "-x", "assembler-with-cpp"]
    config = attempt / "tools.json"; config.write_text(json.dumps(configuration, indent=2) + "\n")
    run([sys.executable, "-X", "utf8", "-B", ROOT / "scripts/prepare-portable-decomp.py", "--source", decomp / "configure.py",
         "--output", stage / "configure-portable.py", "--tools", config], logs / "configure.log", attempt, env)
    run([python, "-X", "utf8", "-B", stage / "configure-portable.py"], logs / "configure.log", stage, env)
    # Each IDO runtime resolves these POSIX paths inside its own isolated root.
    # Override ambient values without changing the caller's environment.
    native = dict(env, TMPDIR="/tmp", USR_LIB="/usr/bin")
    run(["ninja", "-j", args.jobs], logs / "decomp.log", stage, native)
    rebuilt = stage / "build/pokemonsnap.z64"
    if hashlib.sha1(rebuilt.read_bytes()).hexdigest() != lock["rom"]["sha1"]:
        raise ValueError("The complete Windows rebuild did not reproduce the supported ROM")
    host_tools = module_generation.build_host_tools(recut, attempt / "host-tools", args.jobs, env)
    generated = attempt / "generated"
    run([python, "-X", "utf8", "-B", ROOT / "scripts/module_generation.py", "generate", "--source", decomp, "--stage", stage,
         "--output", generated, "--host-tools", next(iter(host_tools.values())).parent,
         "--readelf", paths["readelf"], "--objdump", paths["objdump"], "--rom", stage / "pokemonsnap.z64"], logs / "generation.log", attempt, env)
    run([sys.executable, "-X", "utf8", "-B", ROOT / "scripts/build-game-module.py", "--generated-dir", generated, "--source-dir", recut,
         "--toolchain", toolchain, "--build-dir", attempt / "module", "--jobs", args.jobs], logs / "module.log", attempt, env)
    module = attempt / "module/SnapPadGame.dylib"
    verified_tools(args.tools, args.tools_sha256)
    if sha256(original) != original_hash:
        raise ValueError("The original ROM changed during the build; preserving outputs for diagnosis")
    if key != build_key(original_hash, args.tools_sha256, toolchain) or any(sha256(path) != value for path, value in installed.items()):
        raise ValueError("Build source, toolchain or installed wheel changed; preserving outputs for diagnosis")
    files = [module, stage / "pokemonsnap.z64", rebuilt, stage / "build/pokemonsnap.elf", stage / "build/pokemonsnap.map"]
    files.extend(installed)
    files.extend((attempt / "python/distributions.json", attempt / "python/wheel-installed.json"))
    files.extend(path for path in generated.rglob("*") if path.is_file())
    value = {"schema": 1, "key": key, "module": module.relative_to(work).as_posix(),
             "files": {path.relative_to(work).as_posix(): sha256(path) for path in files}}
    temporary = attempt / "complete.json"; temporary.write_text(json.dumps(value, indent=2) + "\n")
    shutil.copyfile(temporary, work / ("complete-" + attempt.name + ".json"))
    previous = work / "complete.json"
    if previous.exists():
        if linked(previous) or not previous.is_file():
            raise ValueError("Preserving unexpected complete-cache path")
        shutil.copyfile(previous, work / ("complete-before-" + attempt.name + ".json"))
    os.replace(temporary, work / "complete.json")
    write_result(module, work, result)
    return module


def main():
    if os.name == "nt":
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--toolchain", type=Path, required=True)
    parser.add_argument("--tools", type=Path, required=True)
    parser.add_argument("--tools-sha256", required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--decomp-cache", type=Path, help="Optional read-only local Git object cache")
    parser.add_argument("--recut-cache", type=Path, help="Optional read-only local Git object cache")
    parser.add_argument("--jobs", type=int, default=2)
    args = parser.parse_args()
    if args.jobs < 1:
        parser.error("--jobs must be positive")
    try:
        print(build(args))
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        parser.exit(1, str(error) + "\n")


if __name__ == "__main__":
    main()
