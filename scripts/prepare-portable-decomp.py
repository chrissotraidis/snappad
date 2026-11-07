#!/usr/bin/env python3
"""Write an opt-in configure copy; never patch or bootstrap the reference checkout."""
import argparse
import hashlib
from pathlib import Path
import sys

PINNED_CONFIGURE_SHA256 = '206e1dfbfed69e21db2515d7c8856ecf5ecdc3ab8bfbe8befa84257293dd80fc'


def patched_configure(text, configuration):
    text = text.replace('\r\n', '\n')
    if hashlib.sha256(text.encode('utf-8')).hexdigest() != PINNED_CONFIGURE_SHA256:
        raise ValueError('configure.py is not the reviewed pinned source; preserve it and review the new revision')
    text = text.replace('from pathlib import Path\n', 'from pathlib import Path\nsys.path.insert(0, str(Path(__file__).resolve().parent))\nimport portable_decomp\n', 1)
    marker = 'BIN2C = TOOLS_DIR / "bin2c.py"\n'
    text = text.replace(marker, marker + '\nPORTABLE_TOOLS = ' + repr(str(Path(configuration).resolve())) + '\nninja_syntax.Writer = portable_decomp.writer(ninja_syntax.Writer, globals(), PORTABLE_TOOLS)\n', 1)
    text = text.replace('str(s_path)', 's_path.as_posix()').replace('str(c_path)', 'c_path.as_posix()')
    text = text.replace('"ido": TOOLS_DIR / ("ido" + ido) / "cc",', '"ido": portable_decomp.ido_command(PORTABLE_TOOLS, ido),')
    text = text.replace('    linker_entries = split.linker_writer.entries',
                        '    portable_decomp.normalize_generated_text(Path("."))\n\n    linker_entries = split.linker_writer.entries', 1)
    text = text.replace('        setup()\n        sys.exit(0)', '        parser.error("Portable builds require separately verified tools; --setup is disabled")')
    return text


def prepare(source, destination, configuration):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    helper = destination.parent / 'portable_decomp.py'
    if source.parent in destination.parents:
        raise ValueError('Use a separate work stage; the source checkout must remain unchanged')
    if destination.exists() or helper.exists():
        raise ValueError('Preserving existing configure/adapter files; use a new work stage')
    result = patched_configure(source.read_text(encoding='utf-8'), configuration)
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation also refuses a race or unexpected file instead of overwriting it.
    with helper.open('x', encoding='utf-8', newline='\n') as out:
        out.write(Path(__file__).with_name('portable_decomp.py').read_text(encoding='utf-8'))
    with destination.open('x', encoding='utf-8', newline='\n') as out:
        out.write(result)
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True, help='Pinned reference configure.py (read only)')
    parser.add_argument('--output', type=Path, required=True, help='New configure.py in a separately prepared work stage')
    parser.add_argument('--tools', type=Path, required=True, help='Verified tool paths and explicit cpp argv, encoded as JSON')
    args = parser.parse_args()
    print(prepare(args.source, args.output, args.tools))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError) as error:
        sys.exit(str(error))
