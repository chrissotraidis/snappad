#!/usr/bin/env python3
"""Keep native artifact audits wired to their build entry points."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def require(text: str, needle: str, context: str) -> None:
    if needle not in text:
        raise SystemExit(f"missing {context}: {needle}")


def main() -> None:
    cmake = (ROOT / "CMakeLists.txt").read_text(encoding="utf-8")
    runtime_build = (ROOT / "scripts/build-macos-runtime-stack.sh").read_text(
        encoding="utf-8"
    )
    app_build = (ROOT / "scripts/build-macos-app.sh").read_text(encoding="utf-8")
    probe_audit = (ROOT / "scripts/audit-native-link-probe.sh").read_text(
        encoding="utf-8"
    )
    app_audit = (ROOT / "scripts/audit-macos-app.sh").read_text(encoding="utf-8")
    ios_build = (ROOT / "scripts/build-ios-simulator.sh").read_text(encoding="utf-8")
    ios_audit = (ROOT / "scripts/audit-ios-simulator-bundle.sh").read_text(
        encoding="utf-8"
    )

    require(runtime_build, '"$script_dir/audit-native-link-probe.sh"', "probe audit hook")
    require(app_build, '"$script_dir/audit-macos-app.sh" "$app"', "app audit hook")
    require(ios_build, '"$script_dir/verify-generated-evidence.py"', "Simulator evidence gate")
    require(ios_build, '"$script_dir/audit-ios-simulator-bundle.sh" "$app"', "Simulator audit hook")
    for audit, name in ((probe_audit, "probe"), (app_audit, "app")):
        require(audit, 'lipo -archs', f"{name} architecture check")
        require(audit, 'otool -L', f"{name} dependency check")
        require(audit, 'strings', f"{name} embedded-path check")
    bundle_id = "com.chrissotraidis.snappad"
    require(cmake, f'MACOSX_BUNDLE_GUI_IDENTIFIER "{bundle_id}"', "CMake identity")
    require(app_audit, f'[[ "$bundle_id" == "{bundle_id}" ]]', "audited identity")
    for suffix in ("*.z64", "*.n64", "*.v64", "*.elf", "*.map", "*.cpp"):
        require(app_audit, suffix, "forbidden package input")
    require(ios_audit, "IOSSIMULATOR", "Simulator platform check")
    require(ios_audit, "personal_path=", "Simulator personal-path check")
    for suffix in ("z64", "n64", "v64", "elf", "map"):
        require(ios_audit, suffix, "forbidden Simulator package input")

    print("packaging_contract_test: native build audits are fail-closed and wired")


if __name__ == "__main__":
    main()
