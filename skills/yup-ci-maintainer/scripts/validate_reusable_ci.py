#!/usr/bin/env python3
"""Statically validate an EHL plugin's reusable workflow adoption."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


SHA_CALL = re.compile(
    r"uses:\s+EsionHsrahLatigid/yup-actions/\.github/workflows/"
    r"(plugin-ci|plugin-release(?:-signed)?)\.yml@([0-9a-f]{40})"
)

SIGNING_SECRETS = (
    "MACOS_CERTIFICATE_P12_BASE64",
    "MACOS_CERTIFICATE_PASSWORD",
    "APPLE_TEAM_ID",
    "APPLE_API_KEY_ID",
    "APPLE_API_ISSUER_ID",
    "APPLE_API_PRIVATE_KEY_P8_BASE64",
)


def fail(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-signed-release", action="store_true")
    parser.add_argument("repo", nargs="?", default=".", type=Path)
    args = parser.parse_args()
    repo = args.repo.resolve()

    ci_path = repo / ".github" / "workflows" / "ci.yml"
    release_path = repo / ".github" / "workflows" / "release.yml"
    for path in (ci_path, release_path):
        if not path.is_file():
            fail(f"missing {path}")

    matches: dict[str, str] = {}
    for path in (ci_path, release_path):
        text = path.read_text(encoding="utf-8")
        found = SHA_CALL.search(text)
        if not found:
            fail(f"{path} is not pinned to a full yup-actions commit SHA")
        matches[found.group(1)] = found.group(2)

    if len(set(matches.values())) != 1:
        fail(f"CI and release use different yup-actions commits: {matches}")

    release = release_path.read_text(encoding="utf-8")
    if args.require_signed_release:
        if "plugin-release-signed.yml@" not in release:
            fail("release caller is not using plugin-release-signed.yml")
        if not re.search(r"cancel-in-progress:\s*false", release):
            fail("signed release caller must not cancel notarization in progress")
        for secret in SIGNING_SECRETS:
            expected = f"{secret}: ${{{{ secrets.{secret} }}}}"
            if expected not in release:
                fail(f"signed release caller is missing named secret mapping: {secret}")

    ci = ci_path.read_text(encoding="utf-8")
    for key in (
        "product_name:",
        "product_slug:",
        "cmake_option_prefix:",
        "debug_targets_json:",
        "release_test_targets_json:",
        "windows_debug_plugins:",
    ):
        if key not in ci:
            fail(f"CI caller is missing {key}")

    presets_path = repo / "CMakePresets.json"
    try:
        presets = json.loads(presets_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        fail(f"cannot read {presets_path}: {error}")
    release_presets = [
        preset for preset in presets.get("buildPresets", [])
        if preset.get("name") == "plugin-release"
    ]
    if len(release_presets) != 1 or "ehl_stage_products" not in release_presets[0].get("targets", []):
        fail("plugin-release build preset must include ehl_stage_products")

    install_configure = [
        preset for preset in presets.get("configurePresets", [])
        if preset.get("name") == "plugin-install"
    ]
    if len(install_configure) != 1:
        fail("expected exactly one plugin-install configure preset")
    install_configure_preset = install_configure[0]
    if install_configure_preset.get("inherits") != "plugin-release":
        fail("plugin-install configure preset must inherit plugin-release")
    if install_configure_preset.get("cacheVariables", {}).get("EHL_COPY_PLUGIN_AFTER_BUILD") != "ON":
        fail("plugin-install configure preset must set EHL_COPY_PLUGIN_AFTER_BUILD=ON")

    for preset_kind in ("buildPresets", "testPresets"):
        install_presets = [
            preset for preset in presets.get(preset_kind, [])
            if preset.get("name") == "plugin-install"
        ]
        if len(install_presets) != 1:
            fail(f"expected exactly one plugin-install preset in {preset_kind}")
        install_preset = install_presets[0]
        if install_preset.get("inherits") != "plugin-release":
            fail(f"plugin-install preset in {preset_kind} must inherit plugin-release")
        if install_preset.get("configurePreset") != "plugin-install":
            fail(f"plugin-install preset in {preset_kind} must use the plugin-install configure preset")

    for relative in (
        "cmake/EhlYupArtifactLayout.cmake",
        "cmake/StageYupProducts.cmake",
    ):
        if not (repo / relative).is_file():
            fail(f"missing {relative}")

    print(f"repo={repo}")
    print(f"yup_actions_sha={next(iter(matches.values()))}")
    print("local_install_preset=valid")
    print(f"signed_release={'valid' if args.require_signed_release else 'not-required'}")
    print("status=valid")


if __name__ == "__main__":
    main()
