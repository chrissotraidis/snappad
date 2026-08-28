#!/usr/bin/env python3
"""Protect the macOS decomp build from falling back to Apple's cpp driver."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    configure = (ROOT / "ref/pokemonsnap/configure.py").read_text(encoding="utf-8")
    build = (ROOT / "scripts/build-decomp.sh").read_text(encoding="utf-8")
    if 'shutil.which(f"{CROSS}cpp") or shutil.which("cpp")' not in configure:
        raise SystemExit("Pokémon Snap preprocessor selection contract changed")
    for marker in ("command -v cpp-16", "mips-linux-gnu-cpp", 'ln -sfn "$gnu_cpp"'):
        if marker not in build:
            raise SystemExit(f"decomp build lost GNU cpp selection: {marker}")
    if build.find("mips-linux-gnu-cpp") > build.find('uv run configure.py'):
        raise SystemExit("GNU cpp shim must exist before configure.py runs")
    if "filter-decomp-defined-symbols.py" not in build:
        raise SystemExit("decomp build lost compiled-symbol filtering")
    if build.find("filter-decomp-defined-symbols.py") < build.find(
        "recover-decomp-address-symbols.py"
    ):
        raise SystemExit("compiled-symbol filtering must follow undefined recovery")
    print(
        "decomp_cpp_selection_test: cross-prefixed GNU cpp and exact-link "
        "recovery are selected before the final build"
    )


if __name__ == "__main__":
    main()
