import sys
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import subprocess

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import module_generation as module


class ExportedSourceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="Snap stage spaces ")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.source, self.stage = self.root / "source", self.root / "stage"
        self.source.mkdir(); self.stage.mkdir()
        for args in (("init", "-q"), ("config", "user.name", "Synthetic test"),
                     ("config", "user.email", "test@example.invalid"), ("config", "core.autocrlf", "false")):
            self.git(*args)
        for name, data in {"src/test.c": b"int public_fixture;\n", "tools/helper.py": b"# pinned helper\n"}.items():
            for folder in (self.source, self.stage):
                path = folder / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)
        self.git("add", "."); self.git("commit", "-qm", "public synthetic pin")
        patcher = mock.patch.object(module, "verify_source", return_value=self.source)
        self.verify = patcher.start(); self.addCleanup(patcher.stop)

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.source), *args], stderr=subprocess.PIPE)

    def test_export_checks_preserve_checkout_and_allow_private_build_outputs(self):
        before = (self.source / ".git/index").read_bytes()
        (self.stage / "build").mkdir(); (self.stage / "build/fixture.o").write_bytes(b"private fixture")
        files = module.verify_decomp_stage(self.source, self.stage)
        self.assertEqual(set(files), {"src/test.c", "tools/helper.py"})
        self.verify.assert_called_once_with(self.source, "pokemonSnap", ())
        self.assertEqual(before, (self.source / ".git/index").read_bytes())
        self.assertEqual((self.stage / "build/fixture.o").read_bytes(), b"private fixture")

    def test_modified_export_is_rejected_and_preserved(self):
        path = self.stage / "src/test.c"; path.write_bytes(b"unreviewed edit\n")
        with self.assertRaisesRegex(ValueError, "changed or missing"):
            module.verify_decomp_stage(self.source, self.stage)
        self.assertEqual(path.read_bytes(), b"unreviewed edit\n")

    def test_extra_importable_helper_or_scanned_source_is_rejected(self):
        for name in ("src/unexpected.c", "tools/unexpected.py"):
            with self.subTest(name=name):
                path = self.stage / name; path.write_bytes(b"unreviewed source\n")
                with self.assertRaisesRegex(ValueError, "unexpected source files"):
                    module.verify_decomp_stage(self.source, self.stage)
                self.assertTrue(path.exists()); path.unlink()

    def test_generated_line_endings_normalize_without_touching_other_bytes(self):
        path = self.stage / "fixture.cpp"; path.write_bytes(b"one\r\ntwo\n")
        module.normalize_text_files([path]); self.assertEqual(path.read_bytes(), b"one\ntwo\n")
        before = path.stat().st_mtime_ns
        module.normalize_text_files([path]); self.assertEqual(path.stat().st_mtime_ns, before)
        path.write_bytes(b"binary\0\r\n")
        with self.assertRaisesRegex(ValueError, "binary data"):
            module.normalize_text_files([path])
        self.assertEqual(path.read_bytes(), b"binary\0\r\n")

    def test_inventory_paths_match_the_cross_platform_source_filter(self):
        # This source-only scan does not parse YAML; avoid a test dependency on
        # the decomp's separate frozen Python environment.
        with mock.patch.dict(sys.modules, {"yaml": mock.Mock()}):
            inventory = module.load_script("inventory-source-layout", DECOMP=self.stage)
        locations = inventory.source_locations("public_fixture")
        self.assertEqual([item["path"] for item in locations], ["src/test.c"])

    def test_dynamic_audit_uses_the_supplied_host_tool_after_import(self):
        tool = self.root / "portable tools" / "objdump.exe"
        tool.parent.mkdir(); tool.write_bytes(b"synthetic executable")
        tool.chmod(0o755)
        folder = self.root / "private 雪 inputs"; folder.mkdir()
        payload = folder / "payload.bin"; payload.write_bytes(bytes.fromhex("03e00008"))
        audit = module.load_script("audit-dynamic-code", OBJDUMP=tool)
        result = subprocess.CompletedProcess([], 0, "80200000: 03e00008 jr ra\n", "")
        with mock.patch.object(audit.subprocess, "run", return_value=result) as run:
            _, instructions = audit.disassemble(payload)
        self.assertEqual(run.call_args.args[0][0], str(tool.resolve()))
        self.assertEqual(run.call_args.args[0][-1], "payload.bin")
        self.assertEqual(run.call_args.kwargs["cwd"], folder)
        self.assertEqual(instructions, {"jr": 1})

    def test_gnu_tools_receive_basenames_in_the_artifact_directory(self):
        folder = self.root / "private 雪 inputs"; folder.mkdir()
        elf, obj = folder / "pokemonsnap.elf", folder / "fixture.o"
        with mock.patch.dict(sys.modules, {"yaml": mock.Mock()}):
            config = module.load_script("generate-n64recomp-config", ELF=elf)
        output = subprocess.CompletedProcess([], 0, "public listing", "")
        with mock.patch.object(config.subprocess, "run", return_value=output) as run:
            self.assertEqual(config.run_readelf("-h"), "public listing")
            self.assertEqual(run.call_args.args[0][-1], elf.name)
            self.assertEqual(run.call_args.kwargs["cwd"], folder)
            self.assertEqual(config.run_objdump_range(0x80000000, 0x80000004), "public listing")
            self.assertEqual(run.call_args.args[0][-1], elf.name)
            self.assertEqual(run.call_args.kwargs["cwd"], folder)
            with mock.patch.object(config, "parse_symbols", return_value=["parsed"]) as parse:
                self.assertEqual(config.read_object_symbols(obj), ["parsed"])
                parse.assert_called_once_with("public listing")
            self.assertEqual(run.call_args.args[0][-1], obj.name)
            self.assertEqual(run.call_args.kwargs["cwd"], folder)

    def test_generation_refuses_output_inside_either_read_only_input_tree(self):
        for parent in (self.source, self.stage):
            output = parent / "new-private-output"
            with self.assertRaisesRegex(ValueError, "outside the read-only"):
                module.generate(self.source, self.stage, output, {}, None, None, None)
            self.assertFalse(output.exists())

    def test_rebuild_snapshot_detects_added_and_removed_objects(self):
        build = self.stage / "build"; build.mkdir()
        for name in ("pokemonsnap.z64", "pokemonsnap.elf", "pokemonsnap.map", "old.o"):
            (build / name).write_bytes(b"synthetic input")
        rom = build / "pokemonsnap.z64"
        before = module.rebuild_inputs(self.stage, rom)
        added = build / "new.o"; added.write_bytes(b"new object")
        self.assertNotEqual(before, module.rebuild_inputs(self.stage, rom))
        added.unlink(); self.assertEqual(before, module.rebuild_inputs(self.stage, rom))
        (build / "old.o").unlink()
        self.assertNotEqual(before, module.rebuild_inputs(self.stage, rom))


class WindowsCompilerTests(unittest.TestCase):
    def check_selection(self, host, arm_available, expected_arch):
        import types
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            installer = root / 'Microsoft Visual Studio/Installer/vswhere.exe'
            installer.parent.mkdir(parents=True); installer.touch()
            old, new = root / 'older-x64', root / 'newer-arm'
            for installation, arch in ((old, 'x64'), (new, 'arm64')):
                compiler = installation / f'VC/Tools/MSVC/14.44/bin/Host{arch}/{arch}/cl.exe'
                compiler.parent.mkdir(parents=True); compiler.touch()
            selected = new if expected_arch == 'arm64' else old
            calls = []
            def query(command, **kwargs):
                calls.append(command)
                self.assertEqual(kwargs['encoding'], 'utf-8')
                self.assertEqual(command[-1], '-utf8')
                return str(new if '-requiresAny' in command and arm_available else old)
            process = types.SimpleNamespace(stdout='PATH=prepared-compiler\nTEMP=private 雪 path\n')
            original = {'ProgramFiles(x86)': str(root), 'TEMP': 'private 雪 path'}
            with mock.patch.object(module, 'os', types.SimpleNamespace(name='nt', environ=original)), \
                    mock.patch.object(module.platform, 'machine', return_value=host), \
                    mock.patch.object(module.shutil, 'which', side_effect=[None, 'cl.exe']), \
                    mock.patch.object(module.subprocess, 'check_output', side_effect=query), \
                    mock.patch.object(module.subprocess, 'run', return_value=process) as run:
                prepared = module.generator_environment()
            self.assertEqual('-requiresAny' in calls[0], host == 'ARM64')
            self.assertIn(str(selected / 'VC/Auxiliary/Build/vcvarsall.bat'), run.call_args.args[0])
            self.assertIn(' ' + expected_arch + ' >nul', run.call_args.args[0])
            self.assertIn(' /u /d /s /c ', run.call_args.args[0])
            self.assertEqual(run.call_args.kwargs['encoding'], 'utf-16le')
            self.assertEqual(prepared['TEMP'], 'private 雪 path')
            self.assertEqual(original, {'ProgramFiles(x86)': str(root), 'TEMP': 'private 雪 path'})

    def test_newer_arm_only_install_does_not_hide_x64_compiler(self):
        self.check_selection('AMD64', True, 'x64')

    def test_arm_host_keeps_native_compiler_preference(self):
        self.check_selection('ARM64', True, 'arm64')

    def test_arm_host_keeps_x64_fallback(self):
        self.check_selection('ARM64', False, 'x64')

if __name__ == "__main__":
    unittest.main()
