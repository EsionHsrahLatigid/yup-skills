---
name: yup-build-plugin
description: Build, test, stage, and inspect EHL audio plugin repositories based on YUP and CMake presets. Use when working in a YUP plugin repo that has engine-debug and plugin-release presets, when a user cannot find built Standalone/VST3/AU products, when validating the stable artifacts tree contract, or when diagnosing local build and codesign failures.
---

# YUP Plugin Builder

Build through the repository's named CMake presets and treat `artifacts/` as the human-facing output. Keep `build/` as an internal compiler/dependency workspace.

## Workflow

1. Confirm the current directory contains `CMakeLists.txt` and `CMakePresets.json`.
2. Read the project README and preset definitions before running commands. Preserve project-specific options and target names.
3. For a fast DSP check, run:

   ```sh
   cmake --preset engine-debug
   cmake --build --preset engine-debug --parallel
   ctest --preset engine-debug --output-on-failure
   ```

4. For distributable local products, run:

   ```sh
   cmake --preset plugin-release
   cmake --build --preset plugin-release --parallel
   ctest --preset plugin-release --output-on-failure
   ```

5. Run `python3 scripts/verify_artifacts.py <repo>` from this skill directory. Pass `--codesign` on macOS when signatures are part of the claim.
6. Report the exact `artifacts/plugin-release/<platform-arch>` path and the formats found. Do not direct humans into YUP's generator-dependent subdirectories under `build/`.

## Failure handling

- If configure fails while fetching dependencies, retry at most three times with short backoff; preserve the first and final errors.
- If `ehl_stage_products` is missing, inspect `cmake/EhlYupArtifactLayout.cmake`, `cmake/StageYupProducts.cmake`, the call in `CMakeLists.txt`, and the `plugin-release` build preset.
- If staging reports multiple matching bundles, remove only stale build directories after confirming their exact scope; never broadly delete the repository.
- If tests fail, stop packaging claims and report the failing test command and output.
- On macOS, verify all staged `.app`, `.vst3`, and `.component` bundles with `codesign --verify --deep --strict`.

Read [references/artifact-contract.md](references/artifact-contract.md) when adopting or changing the shared output structure.
