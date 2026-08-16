---
name: yup-build-plugin
description: Build, test, stage, install, and inspect EHL audio plugin repositories based on YUP and CMake presets. Use when working in a YUP plugin repo that has engine-debug and plugin-release presets, when a user cannot find built or user-installed Standalone/VST3/AU products, when validating the stable artifacts and local macOS plugin-copy contract, or when diagnosing local build and codesign failures.
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

4. For ordinary distributable products, run:

   ```sh
   cmake --preset plugin-release
   cmake --build --preset plugin-release --parallel
   ctest --preset plugin-release --output-on-failure
   ```

   A fresh local macOS configure defaults the copy option to `ON`; CI and non-macOS configure default it to `OFF`.

5. For a guaranteed local macOS install, prefer the explicit install preset:

   ```sh
   cmake --preset plugin-install
   cmake --build --preset plugin-install --parallel
   ctest --preset plugin-install --output-on-failure
   ```

   If the repository does not yet provide `plugin-install`, configure `plugin-release` with `-DEHL_COPY_PLUGIN_AFTER_BUILD=ON` before building it. Pass the option explicitly because an older CMake cache may retain `OFF` even though a fresh local macOS configure defaults to `ON`. The install path copies VST3 and AU bundles into the current user's plugin folders; Standalone applications remain in `artifacts/`.
6. Run `python3 scripts/verify_artifacts.py <repo>` from this skill directory. On macOS, pass `--installed --codesign` to prove that the user-installed bundles are physical copies matching the staged content and that both copies have valid signatures.
7. Report the exact `artifacts/plugin-release/<platform-arch>` path plus the installed VST3/AU paths. Do not direct humans into YUP's generator-dependent subdirectories under `build/`.

For repositories without `plugin-install`, force or redirect local installation at configure time when required:

```sh
cmake --preset plugin-release -DEHL_COPY_PLUGIN_AFTER_BUILD=ON
cmake --preset plugin-release \
  -DEHL_COPY_PLUGIN_AFTER_BUILD=ON \
  -DEHL_USER_VST3_DIR=/alternate/VST3 \
  -DEHL_USER_AU_DIR=/alternate/Components
```

Use `-DEHL_COPY_PLUGIN_AFTER_BUILD=OFF` only when staging without touching user plugin folders is intentional.

## Failure handling

- If configure fails while fetching dependencies, retry at most three times with short backoff; preserve the first and final errors.
- If `ehl_stage_products` is missing, inspect `cmake/EhlYupArtifactLayout.cmake`, `cmake/StageYupProducts.cmake`, the call in `CMakeLists.txt`, and the `plugin-release` build preset.
- If staging reports multiple matching bundles, remove only stale build directories after confirming their exact scope; never broadly delete the repository.
- If tests fail, stop packaging claims and report the failing test command and output.
- If a local plugin copy differs from the staged bundle, rebuild `ehl_stage_products`; do not repair it by copying an internal YUP build directory.
- On macOS, verify all staged and installed `.app`, `.vst3`, and `.component` bundles with `codesign --verify --deep --strict`.

Read [references/artifact-contract.md](references/artifact-contract.md) when adopting or changing the shared output structure.
