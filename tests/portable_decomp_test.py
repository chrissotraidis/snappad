import ast
import hashlib
import importlib.util
import io
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


portable = load('portable_decomp', ROOT / 'scripts/portable_decomp.py')
prepare = load('prepare_portable_decomp', ROOT / 'scripts/prepare-portable-decomp.py')


class PortableRulesTests(unittest.TestCase):
    def test_assembly_transcodes_bytes_and_propagates_failure(self):
        tools = {'cpp': ['compiler path', '-E', '-x', 'assembler-with-cpp'], 'as': 'assembler path'}
        with mock.patch.object(portable.subprocess, 'check_output', return_value='日本語\n'.encode()) as cpp, mock.patch.object(portable.subprocess, 'run') as asm:
            portable.assemble(tools, Path('input space.s'), Path('output space.o'), ['-I', 'include'])
        self.assertEqual(cpp.call_args.args[0], ['compiler path', '-E', '-x', 'assembler-with-cpp', '-I', 'include', 'input space.s', '-o', '-'])
        self.assertEqual(asm.call_args.kwargs['input'], '日本語\n'.encode('euc_jp'))
        self.assertIn('output space.o', asm.call_args.args[0])
        self.assertIn('-32', asm.call_args.args[0])
        with mock.patch.object(portable.subprocess, 'check_output', side_effect=subprocess.CalledProcessError(1, 'cpp')), mock.patch.object(portable.subprocess, 'run') as asm:
            with self.assertRaises(subprocess.CalledProcessError): portable.assemble(tools, 'in', 'out', [])
            asm.assert_not_called()

    def test_compile_then_abi_fix_with_spaces(self):
        with tempfile.TemporaryDirectory(prefix='snap compiler test ') as temp:
            folder = Path(temp); compiler = folder / 'compiler fixture.py'; fixer = folder / 'abi fixture.py'; output = folder / 'object file.o'
            compiler.write_text('import pathlib,sys;pathlib.Path(sys.argv[1]).write_bytes(b"compiled")')
            fixer.write_text('import pathlib,sys;p=pathlib.Path(sys.argv[1]);assert p.read_bytes()==b"compiled";p.write_bytes(b"fixed")')
            portable.compile_object([sys.executable, str(compiler), str(output)], fixer, output)
            self.assertEqual(output.read_bytes(), b'fixed')
            with mock.patch.object(portable.subprocess, 'run', side_effect=subprocess.CalledProcessError(2, 'compiler')) as run:
                with self.assertRaises(subprocess.CalledProcessError): portable.compile_object(['compiler'], fixer, output, 'strip')
                self.assertEqual(run.call_count, 1)

    def test_checksum_only_stamps_matching_complete_output(self):
        with tempfile.TemporaryDirectory(prefix='snap checksum ') as temp:
            folder = Path(temp); rom = folder / 'game copy.z64'; rom.write_bytes(b'synthetic ROM')
            checksum = folder / 'checksum.sha1'; stamp = folder / 'complete.ok'
            checksum.write_text(hashlib.sha1(rom.read_bytes()).hexdigest() + '  ' + str(rom) + '\n')
            portable.checksum(checksum, stamp); self.assertTrue(stamp.exists()); stamp.unlink()
            for bad in ('', 'not-a-digest  ' + str(rom), '0' * 40 + '  ' + str(rom)):
                checksum.write_text(bad)
                with self.assertRaises(ValueError): portable.checksum(checksum, stamp)
                self.assertFalse(stamp.exists())

    def test_embedded_python_script_sibling_import(self):
        with tempfile.TemporaryDirectory(prefix='snap embedded test ') as temp:
            folder = Path(temp); (folder / 'sibling.py').write_text('VALUE = 42\n')
            script = folder / 'effect fixture.py'; script.write_text('import sibling,sys;assert sibling.VALUE==42;assert sys.argv[1:]==["input file", "output file"]')
            subprocess.run([sys.executable, '-I', '-B', str(ROOT / 'scripts/portable_decomp.py'), 'python', '--script', str(script), '--', 'input file', 'output file'], check=True)
            self.assertFalse((folder / '__pycache__').exists())
            script.write_text('raise SystemExit(3)')
            failed = subprocess.run([sys.executable, '-I', str(ROOT / 'scripts/portable_decomp.py'), 'python', '--script', str(script)])
            self.assertEqual(failed.returncode, 3)

    @unittest.skipUnless(shutil.which('ninja'), 'requires public Ninja executable')
    def test_ninja_runs_python_rule_with_spaced_paths(self):
        with tempfile.TemporaryDirectory(prefix='snap ninja space ') as temp:
            folder = Path(temp); configuration = folder / 'tools with spaces.json'
            tools = {name: sys.executable for name in portable.TOOLS}; tools['cpp'] = [sys.executable]
            configuration.write_text(json.dumps(tools))
            (folder / 'sibling.py').write_text('VALUE = 42\n')
            script = folder / 'bin2c fixture.py'; script.write_text('from pathlib import Path;import sys,sibling;assert sibling.VALUE==42;Path(sys.argv[2]).write_bytes(Path(sys.argv[1]).read_bytes());raise SystemExit(0)')
            incoming = folder / 'input file.bin'; incoming.write_bytes(b'synthetic input\r\n')
            captured = {}
            class Writer:
                def rule(self, name, **kwargs): captured[name] = kwargs['command']
                def build(self, **kwargs): captured['edge'] = kwargs
            context = {'COMMON_INCLUDES': '-I include', 'RAW_BUILD_PREAMBLE': '$ido -O2 $flags', 'GAME_CC_CMD': 'asm --input-enc=utf-8 --output-enc=EUC-JP ido -- as -- -c -o $out $in', 'LIBULTRA_AS_CMD': 'ido -c -o $out $in && fixer $out', 'O32_TOOL': script, 'BIN2C': script}
            writer = portable.writer(Writer, context, configuration)()
            for name in ('bin', 'as', 'as_libultra', 'cc', 'cc_raw', 'cc_libultra', 'ld', 'sha1sum', 'elf', 'z64', 'pigment', 'bin2c', 'effect_sprites', 'vpk0_compress'):
                writer.rule(name, command='unused')
                self.assertNotIn(' && ', captured[name]); self.assertNotIn('bash ', captured[name]); self.assertNotIn('iconv ', captured[name])
            self.assertIn(' -32 ', captured['cc'])
            with self.assertRaises(ValueError): writer.rule('unexpected-new-upstream-rule', command='x')
            writer.build([r'build\nested\out.o'], 'cc', [r'ultralib\audio\input.c'],
                         implicit=[r'build\texture.inc'], implicit_outputs=[r'build\out.d'],
                         order_only=[r'build\ready'], variables={'ido': r'V:\tool folder\cc.exe'})
            edge = captured['edge']
            self.assertEqual(edge['outputs'], ['build/nested/out.o'])
            self.assertEqual(edge['inputs'], ['ultralib/audio/input.c'])
            self.assertEqual(edge['implicit'], ['build/texture.inc'])
            self.assertEqual(edge['implicit_outputs'], ['build/out.d'])
            self.assertEqual(edge['order_only'], ['build/ready'])
            self.assertEqual(edge['variables']['ido'], r'V:\tool folder\cc.exe')
            (folder / 'build.ninja').write_text('rule convert\n  command = ' + captured['bin2c'] + '\nbuild output$ file.bin: convert input$ file.bin\n')
            subprocess.run([shutil.which('ninja'), '-f', 'build.ninja'], cwd=folder, check=True, capture_output=True)
            self.assertEqual((folder / 'output file.bin').read_bytes(), b'synthetic input\n')
            self.assertFalse((folder / '__pycache__').exists())

    def test_native_and_ninja_quoting(self):
        self.assertEqual(portable.command(['C:/tool folder/python.exe', '$flags', '$in'], windows=True), '"C:/tool folder/python.exe" $flags $in')
        self.assertEqual(portable.command(['tool$cash', '$out'], windows=True), 'tool$$cash $out')
        self.assertIn("'tool path'", portable.command(['tool path', '$out'], windows=False))

    def test_generated_text_uses_lf_without_touching_binary_or_source_files(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            files = {'assets/animation.inc.c': b'#define NAME hello\r\n',
                     'asm/function.s': b'.text\r\n', 'assets/bytes.bin': b'\r\n\0',
                     'src/original.c': b'original\r\n', 'assets/already.h': b'LF\n'}
            for name, data in files.items():
                path = root / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)
            before = (root / 'assets/already.h').stat().st_mtime_ns
            portable.normalize_generated_text(root)
            self.assertEqual((root / 'assets/animation.inc.c').read_bytes(), b'#define NAME hello\n')
            self.assertEqual((root / 'asm/function.s').read_bytes(), b'.text\n')
            for name in ('assets/bytes.bin', 'src/original.c', 'assets/already.h'):
                self.assertEqual((root / name).read_bytes(), files[name])
            self.assertEqual((root / 'assets/already.h').stat().st_mtime_ns, before)

    def test_preparation_refuses_unknown_source_and_preserves_existing_files(self):
        fixture = 'from pathlib import Path\nBIN2C = TOOLS_DIR / "bin2c.py"\nstr(c_path)\nstr(s_path)\n'
        with tempfile.TemporaryDirectory(prefix='snap preparation ') as temp:
            folder = Path(temp); source = folder / 'reference/configure.py'; source.parent.mkdir(); source.write_text(fixture)
            out = folder / 'new work/configure.py'
            with self.assertRaises(ValueError): prepare.prepare(source, out, folder / 'tools.json')
            self.assertFalse(out.parent.exists()); self.assertEqual(source.read_text(), fixture)
            with mock.patch.object(prepare, 'PINNED_CONFIGURE_SHA256', hashlib.sha256(fixture.encode()).hexdigest()):
                prepare.prepare(source, out, folder / 'tools with spaces.json')
                self.assertIn('c_path.as_posix()', out.read_text()); self.assertIn('s_path.as_posix()', out.read_text())
                before = out.read_bytes()
                with self.assertRaises(ValueError): prepare.prepare(source, out, folder / 'tools.json')
                self.assertEqual(out.read_bytes(), before)
                with self.assertRaises(ValueError): prepare.prepare(source, source.parent / 'other.py', folder / 'tools.json')
                with self.assertRaises(ValueError): prepare.prepare(source, source.parent / 'nested/configure.py', folder / 'tools.json')
            self.assertEqual(source.read_text(), fixture)


@unittest.skipUnless((ROOT / 'ref/pokemonsnap/configure.py').is_file(), 'requires the pinned public configure.py (no ROM)')
class PinnedGraphTests(unittest.TestCase):
    def graph(self, text, windows, tool_config):
        class Segment:
            def __init__(self, kind): self.type = kind
        names = ('CommonSegC', 'CommonSegAsm', 'CommonSegData', 'CommonSegBin', 'CommonSegTextbin', 'CommonSegGroup', 'N64SegHeader', 'N64SegImg', 'N64SegPalette')
        kinds = {name: type(name, (Segment,), {}) for name in names}
        common = types.SimpleNamespace(**{key: types.SimpleNamespace(**{name: kinds[name]}) for key, name in [('c', 'CommonSegC'), ('asm', 'CommonSegAsm'), ('data', 'CommonSegData'), ('bin', 'CommonSegBin'), ('textbin', 'CommonSegTextbin'), ('group', 'CommonSegGroup')]})
        n64 = types.SimpleNamespace(**{key: types.SimpleNamespace(**{name: kinds[name]}) for key, name in [('header', 'N64SegHeader'), ('img', 'N64SegImg'), ('palette', 'N64SegPalette')]})
        captured = []
        class Writer:
            def __init__(self, *args, **kwargs): pass
            def rule(self, *args, **kwargs): pass
            def build(self, *args, **kwargs): captured.append(kwargs)
        path_type = PureWindowsPath if windows else PurePosixPath
        # Execute only public constants and graph construction, never configure's splitter/setup/main.
        nodes = [n for n in ast.parse(text).body if isinstance(n, ast.FunctionDef) and n.name == 'create_build_script']
        context = {'Path': path_type, 'ROOT': path_type('.'), 'TOOLS_DIR': path_type('tools'), 'ninja_syntax': types.SimpleNamespace(Writer=Writer), 'splat': types.SimpleNamespace(segtypes=types.SimpleNamespace(common=common, n64=n64)), 'List': list, 'Dict': dict, 'Set': set, 'Union': __import__('typing').Union, 'LinkerEntry': object, 'ELF_PATH': 'build/game.elf', 'LD_PATH': 'game.ld', 'MAP_PATH': 'build/game.map', 'Z64_PATH': 'build/game.z64', 'OK_PATH': 'build/game.ok', 'GAME_CC_CMD': '', 'RAW_CC_CMD': '', 'LIBULTRA_CC_CMD': '', 'LIBULTRA_AS_CMD': '', 'CROSS_CPP': 'cpp', 'CROSS_AS': 'as', 'CROSS_LD': 'ld', 'CROSS_OBJCOPY': 'objcopy', 'COMMON_INCLUDES': '', 'PIGMENT64': 'pigment64', 'BIN2C': 'bin2c.py', 'sys': sys, 'portable_decomp': portable, 'PORTABLE_TOOLS': tool_config}
        exec(compile(ast.Module(body=nodes, type_ignores=[]), '<pinned graph>', 'exec'), context)
        filenames = ['src/osFlash.c', 'src/26D80.c', 'src/98C330.c', 'src/848B50.c', 'ultralib/src/os/timer.c', 'ultralib/src/os/initialize.c', 'ultralib/src/io/aisetfreq.c', 'ultralib/src/gu/color.c', 'ultralib/src/sp/spriteex2.c', 'ultralib/src/libc/ll.c', 'ultralib/src/audio/abiplayer.c', 'ultralib/src/os/exceptasm.s', 'ultralib/src/os/helper.s', 'src/header.s']
        entries = [types.SimpleNamespace(segment=kinds['CommonSegC' if name.endswith('.c') else 'CommonSegAsm']('c' if name.endswith('.c') else 'asm'), object_path=path_type('build/' + name + '.o'), src_paths=[path_type(name)]) for name in filenames]
        with mock.patch('builtins.open', return_value=io.StringIO()): context['create_build_script'](entries)
        result = []
        for edge in captured:
            if edge.get('rule') not in ('cc', 'cc_raw', 'cc_libultra', 'as', 'as_libultra'): continue
            variables = dict(edge['variables'])
            if 'ido' in variables:
                value = str(variables['ido']); variables['ido'] = '7.1' if ('ido7.1' in value or 'ido71' in value) else '5.3'
            result.append((edge['rule'], variables))
        return result

    def test_windows_paths_keep_all_representative_mac_compiler_choices(self):
        text = (ROOT / 'ref/pokemonsnap/configure.py').read_text()
        with tempfile.TemporaryDirectory(prefix='snap compiler choices ') as temp:
            folder = Path(temp); config = folder / 'tools.json'; tools = {}
            for name in portable.TOOLS:
                path = folder / name; path.touch(); tools[name] = str(path)
            tools['cpp'] = [sys.executable]; config.write_text(json.dumps(tools))
            original = self.graph(text, False, config)
            native_windows_before = self.graph(text, True, config)
            portable_windows = self.graph(prepare.patched_configure(text, config), True, config)
            self.assertNotEqual(original, native_windows_before)
            self.assertEqual(original, portable_windows)


if __name__ == '__main__': unittest.main()
