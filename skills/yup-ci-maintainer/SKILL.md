---
name: yup-ci-maintainer
description: Adopt, review, pin, and validate the reusable GitHub Actions CI and release workflows used by EHL YUP audio plugin repositories. Use when creating or updating .github/workflows/ci.yml and release.yml, reducing duplicated macOS and Windows build logic, checking compiler caching and artifact ZIPs, updating the yup-actions commit pin, or verifying that exact-SHA release promotion remains fail-closed.
---

# YUP CI Maintainer

Keep triggers, permissions, concurrency, and product inputs in each plugin repository. Keep build classification, macOS/Windows execution, packaging, checksum generation, and exact-SHA release promotion in `EsionHsrahLatigid/yup-actions`.

## Adoption workflow

1. Read the existing caller workflows, CMake options, test targets, presets, and artifact helper registration.
2. Confirm the repository can build `ehl_stage_products` locally before changing CI.
3. Pin reusable workflow calls to a full 40-character commit SHA, never a floating branch or tag.
4. Keep `.github/workflows/ci.yml` named `CI` and `.github/workflows/release.yml` named `Release`; release provenance queries depend on the CI path and name.
5. Supply exact `product_name`, lowercase `product_slug`, uppercase `cmake_option_prefix`, Debug targets, and Release test targets.
6. Enable `windows_debug_plugins` only when Debug plugin/standalone coverage is intentional.
7. Run `actionlint`, then `python3 scripts/validate_reusable_ci.py <repo>` from this skill directory.
8. Push one pilot repository and require macOS arm64, Windows x64, and `CI Summary` to succeed before rolling the same central SHA out further.

When changing `plugin-release-signed.yml` itself, also run the central repository's `scripts/validate_signed_release_workflow.py` and Python regression suite before creating a caller pin candidate.

## Change workflow

1. Change and validate `yup-actions` first.
2. Commit and push it, then capture the immutable full commit SHA.
3. Update callers to that SHA in a separate, reviewable commit.
4. Do not rewrite callers to a new pin until the central commit exists publicly.
5. Re-run a real caller CI; validating only the central YAML cannot prove cross-repository permissions, runner behavior, or artifact paths.

## Required guarantees

- Heavy compilation is skipped for documentation-only changes.
- macOS uses `sccache` through compiler launcher variables.
- Windows runs on the declared Visual Studio runner/generator and executes tests with `-C`.
- Latest artifacts contain one platform ZIP and one SHA-256 manifest, retained for 14 days.
- Tag releases rebuild nothing; they promote artifacts from exactly one successful `main` push CI run for the tag commit.
- A tagless `canary_sha` is non-publishing only. It must be a lowercase full commit SHA equal to GitHub's current `main` HEAD, resolve exactly one successful canonical `main` push CI run, and verify the macOS ZIP plus `SHA256SUMS.txt` before the protected signing environment is requested.
- `tag_name` and `canary_sha` are mutually exclusive. Keep the publishing tag provenance and GitHub Release path locked when changing canary behavior.
- Release publication verifies tag/project version equality, checksums, ZIP integrity, and the final two-asset set.
- Each caller exposes `plugin-install` configure/build/test presets. They inherit `plugin-release`, and the configure preset explicitly sets `EHL_COPY_PLUGIN_AFTER_BUILD=ON` so local installation is not dependent on a stale cache value.

Read [references/reusable-workflows.md](references/reusable-workflows.md) before changing workflow inputs or provenance behavior.
