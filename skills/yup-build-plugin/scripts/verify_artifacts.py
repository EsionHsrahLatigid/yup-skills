#!/usr/bin/env python3
"""Verify the stable EHL YUP artifact tree without modifying it."""

from __future__ import annotations

import argparse
import platform
import subprocess
import sys
from pathlib import Path


def fail(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("repo", nargs="?", default=".", type=Path)
    parser.add_argument("--profile", default="plugin-release")
    parser.add_argument("--platform-arch", dest="platform_arch")
    parser.add_argument("--codesign", action="store_true")
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
    au_dir = stage / "au"
    if stage.name.startswith("macos-"):
        au = sorted(au_dir.glob("*.component")) if au_dir.is_dir() else []
        if len(au) != 1:
            fail(f"expected one AU component, found {len(au)}")
        products += au

    if args.codesign:
        if platform.system() != "Darwin":
            fail("--codesign is only valid on macOS")
        for product in products:
            subprocess.run(
                ["codesign", "--verify", "--deep", "--strict", str(product)],
                check=True,
            )

    print(f"stage={stage}")
    for product in products:
        print(f"product={product.relative_to(stage)}")
    print("manifest:")
    print(manifest.read_text(encoding="utf-8").rstrip())


if __name__ == "__main__":
    main()
