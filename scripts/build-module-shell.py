#!/usr/bin/env python3
"""Build an unsigned, ROM-free iOS runtime shell in a separate maintainer folder."""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from module_contract import ROOT, verify_source


def run(*args):
    subprocess.run([str(arg) for arg in args], check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recut", type=Path, required=True)
    parser.add_argument("--sdl", type=Path, required=True)
    parser.add_argument("--zstd", type=Path, default=ROOT / "ref/zstd")
    parser.add_argument("--build-dir", type=Path, default=ROOT / "build/module-shell")
    parser.add_argument("--jobs", type=int, default=2)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if sys.platform != "darwin" or args.jobs < 1:
        parser.error("the empty shell needs a Mac and a positive --jobs count")
    if args.output.exists():
        parser.error("preserving the existing output; choose a new --output filename")
    recut = verify_source(args.recut)
    rsp_hle = verify_source(recut.parent / "mupen64plus-rsp-hle", "mupen64plusRspHle", ())
    sdl = verify_source(args.sdl, "sdl2", ("sdl2",))
    zstd = verify_source(args.zstd, "zstd", ())
    build = args.build_dir.resolve()
    renderer = recut / "lib/rt64"
    host = build / "host-tools"
    sdk = subprocess.check_output(["xcrun", "--sdk", "macosx", "--show-sdk-path"], text=True).strip()
    # These two targets do not link SDL. Its include/library settings satisfy
    # the renderer's configure-time dependency check only.
    run("cmake", "-S", renderer, "-B", host, "-G", "Ninja", "-DCMAKE_BUILD_TYPE=Release",
        f"-DCMAKE_OSX_SYSROOT={sdk}", f"-DCMAKE_RUNTIME_OUTPUT_DIRECTORY={host}",
        "-DRT64_STATIC=ON", "-DRT64_BUILD_TOOLS=ON", f"-DPAPERPAD_ZSTD_SOURCE_DIR={zstd}",
        f"-DSDL2_INCLUDE_DIRS={sdl / 'include'}", "-DSDL2_LIBRARIES=unused-for-host-tools")
    run("cmake", "--build", host, "--parallel", args.jobs, "--target", "file_to_c", "spirv_cross_msl")
    shutil.copyfile(renderer / "build/bin/spirv_cross_msl", host / "spirv_cross_msl")
    (host / "spirv_cross_msl").chmod(0o755)
    dxc = renderer / "src/contrib/dxc/bin/arm64/dxc-macos"
    if not dxc.stat().st_mode & 0o111:
        raise RuntimeError("The staged host DXC must be executable; preserve its source checkout mode")
    run("cmake", "-S", ROOT, "-B", build / "app", "-G", "Xcode", "-DBUILD_TESTING=OFF",
        "-DSNAPPAD_BUILD_MODULE_SHELL=ON", "-DCMAKE_SYSTEM_NAME=iOS", "-DCMAKE_OSX_SYSROOT=iphoneos",
        "-DCMAKE_OSX_ARCHITECTURES=arm64", "-DCMAKE_XCODE_ATTRIBUTE_CODE_SIGNING_ALLOWED=NO",
        f"-DSNAPPAD_RECUT_ROOT={recut}", f"-DSNAPPAD_SDL2_ROOT={sdl}", f"-DSNAPPAD_ZSTD_ROOT={zstd}",
        f"-DSNAPPAD_RT64_HOST_TOOLS={host}", f"-DPython3_EXECUTABLE={sys.executable}",
        f"-DSNAPPAD_GENERATED_ROOT={build / 'no-private-inputs'}")
    run("cmake", "--build", build / "app", "--config", "Release", "--target", "SnapPad", "--",
        "-sdk", "iphoneos", "-jobs", args.jobs, "CODE_SIGNING_ALLOWED=NO")
    app = build / "app/Release-iphoneos/SnapPad.app"
    if not app.is_dir():
        raise RuntimeError("The shell build did not produce SnapPad.app")
    subprocess.run(["codesign", "--remove-signature", str(app)], check=False, capture_output=True)
    run("bash", ROOT / "scripts/audit-ios-device-bundle.sh", app)
    verify_source(recut)
    verify_source(rsp_hle, "mupen64plusRspHle", ())
    verify_source(sdl, "sdl2", ("sdl2",))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.output, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(app.rglob("*")):
            if path.is_file():
                archive.write(path, "Payload/SnapPad.app/" + path.relative_to(app).as_posix())
        archive.write(ROOT / "RIGHTS_AND_LICENSES.md", "RIGHTS_AND_LICENSES.md")
        for label, source in (("ReCut", recut), ("SDL2", sdl), ("zstd", zstd), ("RSP-HLE", rsp_hle)):
            for path in sorted(source.rglob("*")):
                if path.is_file() and path.name.upper().split(".")[0] in ("LICENSE", "COPYING", "NOTICE"):
                    archive.write(path, f"ThirdPartyLicenses/{label}/" + path.relative_to(source).as_posix())
    print(f"Empty shell ready for private module validation: {args.output}")


if __name__ == "__main__":
    main()
