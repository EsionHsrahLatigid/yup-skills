#!/usr/bin/env python3
"""Regression checks for staged-versus-installed YUP bundle verification."""

from __future__ import annotations

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "skills/yup-build-plugin/scripts/verify_artifacts.py"
SPEC = importlib.util.spec_from_file_location("verify_artifacts", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load {SCRIPT}")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class TreeDigestTests(unittest.TestCase):
    def test_file_mode_changes_digest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            staged = root / "staged.vst3"
            installed = root / "installed.vst3"
            for bundle in (staged, installed):
                executable = bundle / "Contents/MacOS/plugin"
                executable.parent.mkdir(parents=True)
                executable.write_bytes(b"plugin")
                executable.chmod(0o755)

            self.assertEqual(MODULE.tree_digest(staged), MODULE.tree_digest(installed))
            (installed / "Contents/MacOS/plugin").chmod(0o644)
            self.assertNotEqual(MODULE.tree_digest(staged), MODULE.tree_digest(installed))

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks are unavailable")
    def test_symlink_target_changes_digest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            staged = root / "staged.vst3"
            installed = root / "installed.vst3"
            staged.mkdir()
            installed.mkdir()
            os.symlink("first", staged / "alias")
            os.symlink("second", installed / "alias")

            self.assertNotEqual(MODULE.tree_digest(staged), MODULE.tree_digest(installed))


if __name__ == "__main__":
    unittest.main()
