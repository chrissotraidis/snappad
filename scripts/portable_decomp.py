#!/usr/bin/env python3
"""Native process rules for a prepared copy of the pinned Snap decomp."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import runpy
import shlex
import subprocess
import sys

TOOLS = ('ido53', 'ido71', 'asm_processor', 'as', 'ld', 'objcopy', 'strip', 'pigment64')


def load_tools(path):
    value = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(value, dict) or set(value) != set(TOOLS) | {'cpp'}:
        raise ValueError('Tool configuration must name exactly: ' + ', '.join((*TOOLS, 'cpp')))
    for name in TOOLS:
        if not isinstance(value[name], str) or not Path(value[name]).is_file():
            raise ValueError('Missing verified tool: ' + name)
    cpp = value['cpp']
    if not isinstance(cpp, list) or not cpp or not all(isinstance(x, str) for x in cpp) or not Path(cpp[0]).is_file():
        raise ValueError('cpp must be a nonempty argv list starting with an existing executable')
    return value


def command(arguments, windows=None):
    """Quote literal argv values for Ninja's host; leave its controlled variables intact."""
    windows = os.name == 'nt' if windows is None else windows
    variables = {'$in', '$out', '$flags', '$ido', '$libultra', '$img_flags', '$img_type', '$mapfile'}
    quoted = []
    for item in arguments:
        value = str(item)
        if value in variables or value == '-DBUILD_VERSION=$libultra':
            quoted.append(value)
        else:
            # Literal dollar signs must survive Ninja expansion before process quoting.
            value = value.replace('$', '$$')
            quoted.append(subprocess.list2cmdline([value]) if windows else shlex.quote(value))
    return ' '.join(quoted)


def ido_command(configuration, version):
    return command([load_tools(configuration)['ido' + version.replace('.', '')]])


def writer(base, context, configuration):
    """Replace commands only; upstream still chooses every edge, flag and compiler."""
    tools = load_tools(configuration)
    python = sys.executable
    adapter = str(Path(__file__).resolve())
    includes = shlex.split(context['COMMON_INCLUDES'])
    raw = shlex.split(context['RAW_BUILD_PREAMBLE'])
    # Only these pinned templates contain tool Paths, which Windows stringifies with '\\'.
    game = shlex.split(context['GAME_CC_CMD'].replace('\\', '/'))
    game[0], game[3], game[5] = tools['asm_processor'], tools['ido71'], tools['as']
    # The portable GNU assembler may default to ELF64 even for vr4300.
    game.insert(6, '-32')
    ultra_as = shlex.split(context['LIBULTRA_AS_CMD'].split(' && ')[0].replace('\\', '/'))
    ultra_as[0] = tools['ido53']
    abi = str(Path(context['O32_TOOL']).resolve())
    # Embeddable/isolated Python ignores PYTHONDONTWRITEBYTECODE. Keep the
    # verified tool directories unchanged when their helper modules are imported.
    helper = [python, '-B', adapter]
    if Path(tools['asm_processor']).suffix == '.py':
        game = helper + ['python', '--script', game[0], '--', *game[1:]]
    compile_helper = helper + ['compile', '--abi-fixer', abi, '--output', '$out']
    commands = {
        'bin': [tools['ld'], '-r', '-b', 'binary', '$in', '-o', '$out'],
        'as': helper + ['assemble', '--tools', str(Path(configuration).resolve()), '--input', '$in', '--output', '$out', '--', *includes],
        'as_libultra': compile_helper + ['--strip', tools['strip'], '--', *ultra_as],
        'cc': game,
        'cc_raw': compile_helper + ['--', *raw, '-DBUILD_VERSION=VERSION_I', '-c', '-o', '$out', '$in'],
        'cc_libultra': compile_helper + ['--', *raw, '-DBUILD_VERSION=$libultra', '-c', '-o', '$out', '$in'],
        'ld': [tools['ld'], '-T', 'undefined_syms.txt', '-T', 'undefined_syms_auto.txt', '-Map', '$mapfile', '-T', '$in', '-o', '$out'],
        'sha1sum': helper + ['checksum', '--manifest', '$in', '--output', '$out'],
        'elf': [tools['objcopy'], '$in', '$out', '-O', 'binary'],
        'z64': [tools['objcopy'], '$in', '$out', '-O', 'binary'],
        'pigment': [tools['pigment64'], 'to-bin', '$img_flags', '-f', '$img_type', '-o', '$out', '$in'],
        'bin2c': helper + ['python', '--script', str(Path(context['BIN2C']).resolve()), '--lf-output', '$out', '--', '$in', '$out'],
        'effect_sprites': helper + ['python', '--script', str(Path('tools/build/effect_sprites.py').resolve()), '--', '$in', '$out'],
        'vpk0_compress': [python, '-B', str(Path('tools/vpk0.py').resolve()), '$in', '$out'],
    }

    class PortableWriter(base):
        def build(self, outputs, rule, inputs=None, **kwargs):
            # IDO derives quoted-include directories using '/', even on Windows.
            # Preserve argv/tool strings; normalize only Ninja's filesystem edges.
            def paths(value):
                if value is None:
                    return None
                if isinstance(value, (list, tuple)):
                    return [paths(item) for item in value]
                return str(value).replace('\\', '/')
            for name in ('implicit', 'implicit_outputs', 'order_only'):
                if name in kwargs:
                    kwargs[name] = paths(kwargs[name])
            return super().build(outputs=paths(outputs), rule=rule, inputs=paths(inputs), **kwargs)

        def rule(self, name, **kwargs):
            if name not in commands:
                raise ValueError('Unreviewed decomp rule: ' + name)
            kwargs['command'] = command(commands[name])
            return super().rule(name, **kwargs)
    return PortableWriter


def assemble(tools, source, output, includes):
    # Capture bytes: Windows text-mode newline conversion must not touch assembly.
    preprocessed = subprocess.check_output([*tools['cpp'], *includes, str(source), '-o', '-'])
    encoded = preprocessed.decode('utf-8').encode('euc_jp')
    subprocess.run([tools['as'], '-32', '-G0', *includes, '-EB', '-mtune=vr4300', '-march=vr4300', '-o', str(output)], input=encoded, check=True)


def compile_object(arguments, abi_fixer, output, strip=None):
    subprocess.run(arguments, check=True)
    subprocess.run([sys.executable, '-B', str(abi_fixer), str(output)], check=True)
    if strip:
        subprocess.run([str(strip), str(output), '-N', 'asdasdasdasd'], check=True)


def normalize_text(path):
    data = path.read_bytes()
    normalized = data.replace(b'\r\n', b'\n')
    if normalized != data:
        path.write_bytes(normalized)


def normalize_generated_text(root):
    # IDO treats CR as part of some macro replacement tokens. Splat's Windows
    # text writes must have the same LF bytes as the pinned Mac generation.
    for folder in ('assets', 'asm'):
        for path in (root / folder).rglob('*'):
            if path.is_file() and path.suffix in ('.c', '.h', '.s'):
                normalize_text(path)


def checksum(manifest, output):
    checked = 0
    for line in Path(manifest).read_text(encoding='utf-8').splitlines():
        if not line.strip():
            continue
        digest, separator, name = line.partition(' ')
        name = name.lstrip(' *')
        if not separator or len(digest) != 40 or any(c not in '0123456789abcdefABCDEF' for c in digest) or not name:
            raise ValueError('Invalid pinned checksum manifest')
        if hashlib.sha1(Path(name).read_bytes()).hexdigest() != digest.lower():
            raise ValueError('Rebuilt ROM does not match the pinned checksum: ' + name)
        checked += 1
    if not checked:
        raise ValueError('Empty checksum manifest')
    Path(output).touch()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    asm = sub.add_parser('assemble')
    asm.add_argument('--tools', required=True)
    asm.add_argument('--input', type=Path, required=True)
    asm.add_argument('--output', type=Path, required=True)
    asm.add_argument('extra', nargs=argparse.REMAINDER)
    cc = sub.add_parser('compile')
    cc.add_argument('--abi-fixer', type=Path, required=True)
    cc.add_argument('--output', type=Path, required=True)
    cc.add_argument('--strip')
    cc.add_argument('extra', nargs=argparse.REMAINDER)
    check = sub.add_parser('checksum')
    check.add_argument('--manifest', type=Path, required=True)
    check.add_argument('--output', type=Path, required=True)
    py = sub.add_parser('python')
    py.add_argument('--script', type=Path, required=True)
    py.add_argument('--lf-output', type=Path)
    py.add_argument('extra', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    extra = getattr(args, 'extra', [])
    if extra[:1] == ['--']:
        extra = extra[1:]
    if args.action == 'assemble':
        assemble(load_tools(args.tools), args.input, args.output, extra)
    elif args.action == 'compile':
        compile_object(extra, args.abi_fixer, args.output, args.strip)
    elif args.action == 'checksum':
        checksum(args.manifest, args.output)
    else:
        # The embedded Python distribution does not add a script's directory to sys.path.
        sys.path.insert(0, str(args.script.resolve().parent))
        sys.argv = [str(args.script), *extra]
        try:
            runpy.run_path(str(args.script), run_name='__main__')
        except SystemExit as error:
            if error.code not in (None, 0):
                raise
        if args.lf_output:
            normalize_text(args.lf_output)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        sys.exit(str(error))
