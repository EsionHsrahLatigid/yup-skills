#!/usr/bin/env python3
"""Verify the stable EHL YUP artifact tree without modifying it."""

from __future__ import annotations

import argparse
import hashlib
import os
import platform
import stat
import subprocess
import sys
from pathlib import Path


def fail(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(1)


def tree_digest(root: Path) -> str:
    """Hash bundle paths, file bytes, and symlink destinations deterministically."""
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix().encode()
        mode = f"{stat.S_IMODE(path.lstat().st_mode):04o}".encode()
        if path.is_symlink():
            digest.update(b"L\0" + relative + b"\0" + mode + b"\0" + os.readlink(path).encode() + b"\0")
        elif path.is_dir():
            digest.update(b"D\0" + relative + b"\0" + mode + b"\0")
        elif path.is_file():
            digest.update(b"F\0" + relative + b"\0" + mode + b"\0")
            with path.open("rb") as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(block)
    return digest.hexdigest()


def manifest_entries(path: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            entries[key] = value
    return entries


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("repo", nargs="?", default=".", type=Path)
    parser.add_argument("--profile", default="plugin-release")
    parser.add_argument("--platform-arch", dest="platform_arch")
    parser.add_argument("--codesign", action="store_true")
    parser.add_argument("--installed", action="store_true")
    parser.add_argument("--vst3-dir", type=Path)
    parser.add_argument("--au-dir", type=Path)
    args = parser.parse_args()

    repo = args.repo.resolve()
    for required in ("CMakeLists.txt", "CMakePresets.json"):
        if not (repo / required).is_file():
            fail(f"{repo} is missing {required}")

    profile_root = repo / "artifacts" / args.profile
    if not profile_root.is_dir():
        fail(f"missing staged profile: {profile_root}")

    if args.platform_arch:
        stage_dirs = [profile_root / args.platform_arch]
    else:
        stage_dirs = sorted(path for path in profile_root.iterdir() if path.is_dir())
    stage_dirs = [path for path in stage_dirs if path.is_dir()]
    if len(stage_dirs) != 1:
        fail(f"expected one platform directory under {profile_root}, found {len(stage_dirs)}")

    stage = stage_dirs[0]
    manifest = stage / "ARTIFACTS.txt"
    if not manifest.is_file():
        fail(f"missing {manifest}")

    standalone = sorted((stage / "standalone").glob("*"))
    vst3 = sorted((stage / "vst3").glob("*.vst3"))
    if len(standalone) != 1 or len(vst3) != 1:
        fail(f"expected one Standalone and one VST3, found {len(standalone)} and {len(vst3)}")

    products = standalone + vst3
    au: list[Path] = []
    au_dir = stage / "au"
    if stage.name.startswith("macos-"):
        au = sorted(au_dir.glob("*.component")) if au_dir.is_dir() else []
        if len(au) != 1:
            fail(f"expected one AU component, found {len(au)}")
        products += au

    installed_products: list[Path] = []
    if args.installed:
        if not stage.name.startswith("macos-"):
            fail("--installed requires a macOS artifact tree")
        if vst3[0].is_symlink():
            fail(f"staged VST3 bundle must be a physical copy: {vst3[0]}")

        vst3_dir = (args.vst3_dir or Path.home() / "Library/Audio/Plug-Ins/VST3").expanduser()
        au_install_dir = (args.au_dir or Path.home() / "Library/Audio/Plug-Ins/Components").expanduser()
        installed_vst3 = vst3_dir / vst3[0].name
        installed_au = au_install_dir / au[0].name
        pairs = [(vst3[0], installed_vst3), (au[0], installed_au)]
        entries = manifest_entries(manifest)
        expected_manifest = {
            "installed_vst3": str(installed_vst3),
            "installed_au": str(installed_au),
        }
        for key, expected in expected_manifest.items():
            if entries.get(key) != expected:
                fail(f"manifest {key} is {entries.get(key)!r}, expected {expected!r}")
        for staged, installed in pairs:
            if not installed.is_dir():
                fail(f"missing installed bundle: {installed}")
            if installed.is_symlink():
                fail(f"installed bundle must be a physical copy, not a symlink: {installed}")
            if tree_digest(staged) != tree_digest(installed):
                fail(f"installed bundle differs from staged bundle: {installed}")
            installed_products.append(installed)

    if args.codesign:
        if platform.system() != "Darwin":
            fail("--codesign is only valid on macOS")
        for product in products + installed_products:
            subprocess.run(
                ["codesign", "--verify", "--deep", "--strict", str(product)],
                check=True,
            )

    print(f"stage={stage}")
    for product in products:
        print(f"product={product.relative_to(stage)}")
    for product in installed_products:
        print(f"installed={product}")
    print("manifest:")
    print(manifest.read_text(encoding="utf-8").rstrip())


if __name__ == "__main__":
    main()
