#!/usr/bin/env python3
"""Keep physical deployment explicit, signed, and data-preserving."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
readiness = (ROOT / "scripts/check-ios-device-readiness.sh").read_text()
deployment = (ROOT / "scripts/deploy-ios-device.sh").read_text()

for marker in (
    "SNAPPAD_APPLE_TEAM_ID",
    "security find-identity -v -p codesigning",
    "xcrun devicectl list devices",
):
    if marker not in readiness:
        raise SystemExit(f"device readiness lost prerequisite: {marker}")

for marker in (
    '[[ -n "$device" ]]',
    'audit-ios-device-bundle.sh',
    'embedded.mobileprovision',
    "xcrun devicectl device install app",
    "xcrun devicectl device process launch --terminate-existing",
    "xcrun simctl list devices",
):
    if marker not in deployment:
        raise SystemExit(f"device deployment lost guardrail: {marker}")

for destructive in ("uninstall", "rm -rf", "erase", "delete app"):
    if destructive in deployment.lower():
        raise SystemExit(f"device deployment contains destructive operation: {destructive}")

print("device_deployment_contract_test: signed in-place deployment guardrails retained")
