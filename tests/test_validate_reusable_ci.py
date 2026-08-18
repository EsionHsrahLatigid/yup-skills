#!/usr/bin/env python3
"""Regression checks for the reusable CI and local-install preset validator."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "skills/yup-ci-maintainer/scripts/validate_reusable_ci.py"
PIN = "1" * 40


class ReusableCiValidatorTests(unittest.TestCase):
    def create_repo(
        self,
        root: Path,
        copy_value: str = "ON",
        signed_release: bool = False,
        include_signing_secrets: bool = True,
    ) -> Path:
        workflows = root / ".github/workflows"
        workflows.mkdir(parents=True)
        (workflows / "ci.yml").write_text(
            "\n".join(
                (
                    "jobs:",
                    "  ci:",
                    f"    uses: EsionHsrahLatigid/yup-actions/.github/workflows/plugin-ci.yml@{PIN}",
                    "    with:",
                    "      product_name: Fixture",
                    "      product_slug: fixture",
                    "      cmake_option_prefix: FIXTURE",
                    "      debug_targets_json: '[]'",
                    "      release_test_targets_json: '[]'",
                    "      windows_debug_plugins: false",
                )
            ),
            encoding="utf-8",
        )
        release_lines = [
            "concurrency:",
            "  cancel-in-progress: false",
            "jobs:",
            "  release:",
            (
                "    uses: EsionHsrahLatigid/yup-actions/.github/workflows/"
                f"{'plugin-release-signed' if signed_release else 'plugin-release'}.yml@{PIN}"
            ),
        ]
        if signed_release and include_signing_secrets:
            release_lines.append("    secrets:")
            for secret in (
                "MACOS_CERTIFICATE_P12_BASE64",
                "MACOS_CERTIFICATE_PASSWORD",
                "APPLE_TEAM_ID",
                "APPLE_API_KEY_ID",
                "APPLE_API_ISSUER_ID",
                "APPLE_API_PRIVATE_KEY_P8_BASE64",
            ):
                release_lines.append(f"      {secret}: ${{{{ secrets.{secret} }}}}")
        (workflows / "release.yml").write_text("\n".join(release_lines), encoding="utf-8")
        presets = {
            "configurePresets": [
                {"name": "plugin-release"},
                {
                    "name": "plugin-install",
                    "inherits": "plugin-release",
                    "cacheVariables": {"EHL_COPY_PLUGIN_AFTER_BUILD": copy_value},
                },
            ],
            "buildPresets": [
                {"name": "plugin-release", "targets": ["ehl_stage_products"]},
                {
                    "name": "plugin-install",
                    "inherits": "plugin-release",
                    "configurePreset": "plugin-install",
                },
            ],
            "testPresets": [
                {"name": "plugin-release"},
                {
                    "name": "plugin-install",
                    "inherits": "plugin-release",
                    "configurePreset": "plugin-install",
                },
            ],
        }
        (root / "CMakePresets.json").write_text(json.dumps(presets), encoding="utf-8")
        cmake = root / "cmake"
        cmake.mkdir()
        for helper in ("EhlYupArtifactLayout.cmake", "StageYupProducts.cmake"):
            (cmake / helper).write_text("# fixture\n", encoding="utf-8")
        return root

    def run_validator(
        self,
        repo: Path,
        *options: str,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *options, str(repo)],
            check=False,
            capture_output=True,
            text=True,
        )

    def test_accepts_explicit_install_preset_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            result = self.run_validator(self.create_repo(Path(temporary_directory)))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("local_install_preset=valid", result.stdout)

    def test_rejects_install_preset_that_keeps_copy_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            result = self.run_validator(
                self.create_repo(Path(temporary_directory), copy_value="OFF")
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("EHL_COPY_PLUGIN_AFTER_BUILD=ON", result.stderr)

    def test_accepts_signed_release_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            repo = self.create_repo(Path(temporary_directory), signed_release=True)
            result = self.run_validator(repo, "--require-signed-release")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("signed_release=valid", result.stdout)

    def test_rejects_signed_release_without_named_secret_mappings(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            repo = self.create_repo(
                Path(temporary_directory),
                signed_release=True,
                include_signing_secrets=False,
            )
            result = self.run_validator(repo, "--require-signed-release")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing named secret mapping", result.stderr)

    def test_rejects_signed_release_that_cancels_notarization(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            repo = self.create_repo(Path(temporary_directory), signed_release=True)
            release = repo / ".github/workflows/release.yml"
            release.write_text(
                release.read_text(encoding="utf-8").replace(
                    "cancel-in-progress: false",
                    "cancel-in-progress: true",
                ),
                encoding="utf-8",
            )
            result = self.run_validator(repo, "--require-signed-release")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must not cancel notarization", result.stderr)


if __name__ == "__main__":
    unittest.main()
