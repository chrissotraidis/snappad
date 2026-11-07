"""Source identity and read-only checks for SnapPad's private module boundary."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def same_source_bytes(actual, expected):
    if actual == expected:
        return True
    if b"\0" in actual or b"\0" in expected:
        return False
    return actual.replace(b"\r\n", b"\n") == expected.replace(b"\r\n", b"\n")


def identity():
    paths = [ROOT / "CMakeLists.txt", ROOT / "dependencies.lock.json", Path(__file__)]
    for folder, suffixes in (("port", (".h", ".cpp", ".mm", ".patch")),
                             ("cmake", (".cmake", ".txt", ".manifest")), ("config", (".json",))):
        paths.extend(path for path in (ROOT / folder).rglob("*") if path.suffix in suffixes)
    digest = hashlib.sha256()
    for path in sorted(set(paths), key=lambda value: value.relative_to(ROOT).as_posix()):
        digest.update(path.relative_to(ROOT).as_posix().encode() + b"\0")
        digest.update(path.read_bytes().replace(b"\r\n", b"\n") + b"\0")
    return digest.hexdigest()


def verify_source(source, key="paperMarioReCut", patch_folders=("n64recomp", "n64modernruntime", "rt64")):
    """Compare the exact pin plus reviewed patches without changing its checkout/index."""
    source = Path(source).resolve()
    lock = json.loads((ROOT / "dependencies.lock.json").read_text())
    env = dict(os.environ, GIT_OPTIONAL_LOCKS="0")

    def git(*args, environment=env, input=None):
        return subprocess.check_output(["git", "-C", str(source), *args], env=environment, input=input)

    if git("rev-parse", "HEAD").decode().strip() != lock["sources"][key]["commit"]:
        raise ValueError(f"Preserving source with a different revision: {source}")
    if any(line.startswith(b"160000 ") for line in git("ls-tree", "-r", "HEAD").splitlines()):
        raise ValueError("This source now contains gitlinks; review their pins before using the module route")
    untracked = set(git("ls-files", "--others", "--exclude-standard", "-z").decode().split("\0")) - {""}
    with tempfile.TemporaryDirectory(prefix="SnapPad source check ") as temporary:
        expected_env = dict(env, GIT_INDEX_FILE=str(Path(temporary) / "index"))
        git("read-tree", "HEAD", environment=expected_env)
        for folder in patch_folders:
            for patch in sorted((ROOT / "port/patches" / folder).glob("*.patch")):
                git("apply", "--cached", "-", environment=expected_env,
                    input=patch.read_bytes().replace(b"\r\n", b"\n"))
        expected = git("diff", "--cached", "--name-only", "-z", "HEAD", environment=expected_env)
        # A reviewed patch can add a source file. Only those exact additions
        # may be untracked in the caller's checkout, and their bytes are checked below.
        unexpected = untracked - set(expected.decode().split("\0"))
        if unexpected:
            raise ValueError(f"Preserving unreviewed source files in {source}: {sorted(unexpected)}")
        actual = git("diff", "--name-only", "-z", "HEAD", "--ignore-submodules=all")
        for name in sorted(set((expected + actual).decode().split("\0")) - {""}):
            path = source / name
            data = git("show", ":" + name, environment=expected_env)
            if (not path.is_file() or path.is_symlink()
                    or not same_source_bytes(path.read_bytes(), data)):
                raise ValueError(f"Preserving unreviewed source changes: {path}")
    return source


def verify_generated(generated):
    generated = Path(generated).resolve()
    spec = importlib.util.spec_from_file_location("snappad_g2_check", ROOT / "scripts/verify-generated-evidence.py")
    verifier = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(verifier)
    for name, relative in {
        "OUT": "evidence/G2-generation.json", "G1_EVIDENCE": "evidence/G1.json",
        "N64_CONFIG": "aot/snappad-us.toml", "RSP_CONFIG": "aot/snappad-audio-rsp.toml",
        "METADATA": "aot/snappad_game_metadata.h", "DYNAMIC_CODE_EVIDENCE": "evidence/G2-dynamic-code.json",
        "CPU_OUTPUT": "aot/snappad_recomp_out", "RSP_OUTPUT": "aot/rsp/aspMain.cpp",
    }.items():
        setattr(verifier.AUDIT, name, generated / relative)
    verifier.main()


def generated_hashes(generated):
    result = {}
    for folder in (Path(generated) / "aot", Path(generated) / "evidence"):
        if folder.is_symlink() or not folder.is_dir():
            raise ValueError(f"Missing or linked generated input folder: {folder}")
        for path in sorted(folder.rglob("*")):
            if path.is_symlink():
                raise ValueError(f"Generated input is a symlink: {path}")
            if path.is_file():
                result[path.relative_to(generated).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def input_record(generated, source):
    verify_source(source)
    verify_generated(generated)
    return {"contract": identity(), "files": generated_hashes(generated)}


def verify_inputs(generated, source, record):
    if json.loads(Path(record).read_text()) != input_record(Path(generated), Path(source)):
        raise ValueError("Private module inputs changed; rerun build-game-module.py")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("identity")
    verify = commands.add_parser("verify")
    verify.add_argument("generated", type=Path)
    verify.add_argument("source", type=Path)
    verify.add_argument("record", type=Path)
    args = parser.parse_args()
    if args.command == "identity":
        print(identity())
    else:
        verify_inputs(args.generated, args.source, args.record)


if __name__ == "__main__":
    main()
