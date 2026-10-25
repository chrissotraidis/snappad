"""Portable regressions for the private Windows orchestration boundary."""
import base64
import csv
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock
import zipfile

SPEC = importlib.util.spec_from_file_location("windows_module_build", Path(__file__).resolve().parents[1] / "scripts/build-windows-module.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def wheel(path, name="rabbitizer", version=MODULE.WHEEL_VERSION):
    info = name + "-" + version + ".dist-info"
    payload = {name + ".pyd": b"synthetic extension", info + "/METADATA": f"Name: {name}\nVersion: {version}\n".encode(),
               info + "/WHEEL": b"Wheel-Version: 1.0\nTag: cp313-cp313-win_amd64\n"}
    rows = [[key, "sha256=" + base64.urlsafe_b64encode(hashlib.sha256(value).digest()).decode().rstrip("="), str(len(value))]
            for key, value in payload.items()]
    rows.append([info + "/RECORD", "", ""])
    text = io.StringIO(newline=""); csv.writer(text).writerows(rows)
    payload[info + "/RECORD"] = text.getvalue().encode()
    with zipfile.ZipFile(path, "w") as archive:
        for key, value in payload.items():
            archive.writestr(key, value)


class WindowsPipelineTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="Snap pipeline spaces ")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()

    def manifest(self):
        tools = self.root / "tools"; tools.mkdir()
        receipt = self.root / "provenance.json"; receipt.write_text("{}\n")
        paths = {}
        for role in MODULE.ROLES:
            path = tools / role
            if role == "rabbitizer_wheel":
                wheel(path)
            elif role.endswith("_wheel"):
                name = role.removesuffix("_wheel")
                wheel(path, name, MODULE.BUILD_WHEELS[name])
            else:
                path.write_bytes(role.encode())
            paths[role] = str(path)
        component = {"root": str(tools), "receipt": str(receipt), "receipt_sha256": MODULE.sha256(receipt),
                     "complete": True, "files": [{"path": path.name, "sha256": MODULE.sha256(path)} for path in tools.iterdir()]}
        return {"schema": 1, "paths": paths, "components": [component],
                "python": {"abi": "cp313-win_amd64", "rabbitizer_version": MODULE.WHEEL_VERSION}}

    def verify(self, value):
        path = self.root / "bundle.json"; path.write_text(json.dumps(value))
        return MODULE.verified_tools(path, MODULE.sha256(path))

    def test_tool_manifest_binds_bytes_receipts_roles_and_complete_inventory(self):
        value = self.manifest(); paths = self.verify(value)
        self.assertEqual(set(paths), MODULE.ROLES)
        extra = self.root / "tools/unexpected.py"; extra.write_text("unreviewed")
        with self.assertRaisesRegex(ValueError, "inventory changed"):
            self.verify(value)
        extra.unlink()
        Path(value["paths"]["cpp"]).write_text("different compiler")
        with self.assertRaisesRegex(ValueError, "changed tool inventory"):
            self.verify(value)

    def test_tool_role_cannot_escape_inventory(self):
        value = self.manifest()
        extra = self.root / "outside.exe"; extra.write_text("outside")
        value["paths"]["cpp"] = str(extra)
        with self.assertRaisesRegex(ValueError, "covered"):
            self.verify(value)
        self.assertEqual(extra.read_text(), "outside")
        with self.assertRaisesRegex(ValueError, "Invalid relative"):
            MODULE.relative_file(self.root, "../outside")

    def test_build_wheel_uses_top_level_metadata_with_vendored_distributions(self):
        value = self.manifest(); path = Path(value["paths"]["setuptools_wheel"])
        with zipfile.ZipFile(path, "a") as archive:
            archive.writestr("vendor/other-1.0.dist-info/METADATA", "Name: other\nVersion: 1.0\n")
        for item in value["components"][0]["files"]:
            if item["path"] == path.name:
                item["sha256"] = MODULE.sha256(path)
        self.verify(value)

    def test_only_ido_can_have_uninventoried_writable_tmp(self):
        value = self.manifest(); original = value["components"][0]
        ido = self.root / "ido"; ido.mkdir()
        files = []
        for role in ("ido53", "ido71"):
            old = Path(value["paths"][role]); new = ido / old.name; old.rename(new)
            value["paths"][role] = str(new)
            files.append({"path": new.name, "sha256": MODULE.sha256(new)})
        original["files"] = [item for item in original["files"] if item["path"] not in ("ido53", "ido71")]
        value["components"].append(dict(original, root=str(ido), kind="ido", files=files))
        temporary = ido / "tmp"; temporary.mkdir(); (temporary / "compiler-temp").write_text("working state")
        self.verify(value)
        asm_temporary = self.root / "tools/tmp"; asm_temporary.mkdir(); (asm_temporary / "extra").write_text("unexpected")
        with self.assertRaisesRegex(ValueError, "inventory changed"):
            self.verify(value)

    def test_ido_tmp_link_is_rejected_before_exclusion(self):
        value = self.manifest(); original = value["components"][0]
        ido = self.root / "ido"; ido.mkdir()
        files = []
        for role in ("ido53", "ido71"):
            old = Path(value["paths"][role]); new = ido / old.name; old.rename(new)
            value["paths"][role] = str(new); files.append({"path": new.name, "sha256": MODULE.sha256(new)})
        original["files"] = [item for item in original["files"] if item["path"] not in ("ido53", "ido71")]
        value["components"].append(dict(original, root=str(ido), kind="ido", files=files))
        outside = self.root / "outside"; outside.mkdir()
        try:
            (ido / "tmp").symlink_to(outside, target_is_directory=True)
        except OSError:
            self.skipTest("This Windows account cannot create symbolic links")
        with self.assertRaisesRegex(ValueError, "Linked tool"):
            self.verify(value)

    def test_installed_wheel_payload_and_record_are_both_checked(self):
        archive = self.root / "candidate.whl"; wheel(archive)
        site = self.root / "site packages"; site.mkdir()
        with zipfile.ZipFile(archive) as incoming:
            incoming.extractall(site)
        files = MODULE.installed_wheel(archive, site)
        extension = site / "rabbitizer.pyd"
        self.assertIn(extension, files)
        extension.write_bytes(b"same version but other binary")
        with self.assertRaisesRegex(ValueError, "payload does not match"):
            MODULE.installed_wheel(archive, site)
        extension.write_bytes(b"synthetic extension")
        record = next(site.glob("*.dist-info/RECORD"))
        record.write_text(record.read_text().replace("sha256=", "invalid=", 1))
        with self.assertRaisesRegex(ValueError, "RECORD does not match"):
            MODULE.installed_wheel(archive, site)

    def test_rom_byte_orders_normalize_without_changing_originals(self):
        data = bytes.fromhex("8037124001020304")
        specification = {"size": len(data), "sha1": hashlib.sha1(data).hexdigest()}
        variants = (data, b"".join(data[i:i + 2][::-1] for i in range(0, len(data), 2)),
                    b"".join(data[i:i + 4][::-1] for i in range(0, len(data), 4)))
        for index, encoded in enumerate(variants):
            source = self.root / f"original {index}"; source.write_bytes(encoded)
            output = self.root / f"normalized {index}"
            MODULE.normalize_rom(source, output, specification)
            self.assertEqual(output.read_bytes(), data); self.assertEqual(source.read_bytes(), encoded)
            with self.assertRaises(FileExistsError):
                MODULE.normalize_rom(source, output, specification)
        wrong = self.root / "wrong"; wrong.write_bytes(b"unknown!")
        output = self.root / "must not exist"
        with self.assertRaisesRegex(ValueError, "byte order"):
            MODULE.normalize_rom(wrong, output, specification)
        self.assertFalse(output.exists())

    def test_complete_cache_checks_referenced_files_and_preserves_stale_data(self):
        module = self.root / "module.dylib"; module.write_bytes(b"module")
        generated = self.root / "generated.c"; generated.write_bytes(b"generated")
        value = {"schema": 1, "key": "key", "module": module.name,
                 "files": {path.name: MODULE.sha256(path) for path in (module, generated)}}
        (self.root / "complete.json").write_text(json.dumps(value))
        self.assertEqual(MODULE.saved_result(self.root, "key"), module)
        self.assertIsNone(MODULE.saved_result(self.root, "changed key"))
        generated.write_bytes(b"changed input")
        self.assertIsNone(MODULE.saved_result(self.root, "key"))
        self.assertEqual(generated.read_bytes(), b"changed input")

    def test_result_and_cache_receipts_cannot_replace_inputs(self):
        result = self.root / "module-result.json"
        for path in (result, self.root / "complete.json"):
            path.write_bytes(b"original private input")
            with self.assertRaisesRegex(ValueError, "must not replace"):
                MODULE.validate_output_paths(self.root, result, [path])
            self.assertEqual(path.read_bytes(), b"original private input")

    def test_sdk_header_and_tbd_changes_invalidate_same_path_cache(self):
        sdk = self.root / "sdk"; sdk.mkdir()
        toolchain = sdk / "toolchain.cmake"; toolchain.write_text("fixed toolchain")
        header = sdk / "stdio.h"; header.write_text("old header")
        stub = sdk / "libSystem.tbd"; stub.write_text("old exports")
        with mock.patch.object(MODULE.module_contract, "identity", return_value="contract"):
            original = MODULE.build_key("rom", "bundle", toolchain)
            self.assertEqual(original, MODULE.build_key("rom", "bundle", toolchain))
            header.write_text("new header")
            self.assertNotEqual(original, MODULE.build_key("rom", "bundle", toolchain))
            header.write_text("old header"); stub.write_text("new exports")
            self.assertNotEqual(original, MODULE.build_key("rom", "bundle", toolchain))


class SourcePreparationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="Snap source spaces "); self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve(); self.cache = self.root / "object cache"; self.cache.mkdir()
        for arguments in (("init", "-q"), ("config", "user.name", "Synthetic"), ("config", "user.email", "test@example.invalid"),
                          ("config", "core.autocrlf", "false")):
            self.git(*arguments)
        (self.cache / "source.txt").write_bytes(b"public\n")
        self.git("add", "."); self.git("commit", "-qm", "public fixture")
        self.commit = self.git("rev-parse", "HEAD").strip()
        self.project = self.root / "project"; self.project.mkdir()
        self.lock = {"sources": {key: {"url": "https://example.invalid/public.git", "commit": self.commit}
                                  for key in ("pokemonSnap", "paperMarioReCut")}}
        self.save_lock()
        for module, name in ((MODULE, "ROOT"), (MODULE.module_contract, "ROOT")):
            patcher = mock.patch.object(module, name, self.project); patcher.start(); self.addCleanup(patcher.stop)
        global_config = self.root / "global.gitconfig"; global_config.write_text("[core]\n autocrlf = true\n")
        self.env = dict(os.environ, GIT_CONFIG_GLOBAL=str(global_config))

    def git(self, *arguments):
        return subprocess.check_output(["git", "-C", str(self.cache), *arguments], text=True, stderr=subprocess.PIPE)

    def save_lock(self):
        (self.project / "dependencies.lock.json").write_text(json.dumps(self.lock))

    def prepare(self, key):
        destination = MODULE.source_destination(self.root / "work", key)
        return MODULE.prepare_source(key, destination, self.env, self.cache)

    def test_new_checkout_is_lf_despite_global_autocrlf_and_cache_stays_read_only(self):
        before = (self.cache / ".git/index").read_bytes()
        (self.cache / "source.txt").write_bytes(b"uncommitted cache work\n")
        source = self.prepare("pokemonSnap")
        self.assertEqual((source / "source.txt").read_bytes(), b"public\n")
        self.assertEqual(subprocess.check_output(["git", "-C", str(source), "config", "core.autocrlf"], text=True).strip(), "false")
        self.assertEqual((self.cache / "source.txt").read_bytes(), b"uncommitted cache work\n")
        self.assertEqual(before, (self.cache / ".git/index").read_bytes())

    def test_new_pin_gets_new_checkout_and_preserves_previous_source(self):
        old = self.prepare("pokemonSnap")
        (self.cache / "source.txt").write_bytes(b"new release\n")
        self.git("add", "."); self.git("commit", "-qm", "next public pin")
        self.lock["sources"]["pokemonSnap"]["commit"] = self.git("rev-parse", "HEAD").strip(); self.save_lock()
        new = self.prepare("pokemonSnap")
        self.assertNotEqual(old, new)
        self.assertEqual((old / "source.txt").read_bytes(), b"public\n")
        self.assertEqual((new / "source.txt").read_bytes(), b"new release\n")

    def test_new_patch_gets_new_checkout_and_preserves_previous_patched_source(self):
        folder = self.project / "port/patches/n64recomp"; folder.mkdir(parents=True)
        patch = folder / "fixture.patch"
        def change(value):
            patch.write_text("diff --git a/source.txt b/source.txt\n--- a/source.txt\n+++ b/source.txt\n@@ -1 +1 @@\n-public\n+" + value + "\n")
        change("first patch"); old = self.prepare("paperMarioReCut")
        change("next patch"); new = self.prepare("paperMarioReCut")
        self.assertNotEqual(old, new)
        self.assertEqual((old / "source.txt").read_bytes(), b"first patch\n")
        self.assertEqual((new / "source.txt").read_bytes(), b"next patch\n")


if __name__ == "__main__":
    unittest.main()
