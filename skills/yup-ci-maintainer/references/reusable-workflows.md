# Reusable YUP workflow contract

Canonical repository: `https://github.com/EsionHsrahLatigid/yup-actions`

Reusable files:

- `.github/workflows/plugin-ci.yml`
- `.github/workflows/plugin-release.yml`
- `.github/workflows/plugin-release-signed.yml`

The CI caller provides:

- `product_name`
- `product_slug`
- `cmake_option_prefix`
- `debug_targets_json`
- `release_test_targets_json`
- `windows_debug_plugins`

The signed release caller provides `product_name`, grants `actions: read` plus `contents: write`, and explicitly maps `MACOS_CERTIFICATE_P12_BASE64`, `MACOS_CERTIFICATE_PASSWORD`, `APPLE_TEAM_ID`, `APPLE_API_KEY_ID`, `APPLE_API_ISSUER_ID`, and `APPLE_API_PRIVATE_KEY_P8_BASE64`.

Use `plugin-release-signed.yml` for public releases after the credentials are installed. It retains exact successful-CI provenance, signs with Developer ID Application, notarizes with an App Store Connect Team API key, staples each bundle, recreates the public ZIP, and re-verifies the exact archive. Keep `plugin-release.yml` only as a migration fallback; do not use it for new public releases after caller migration.

For EHL releases, the certificate, Team ID, and Team API key must all belong to ISHII 2bit Program Office. Never commit or print these values. Individual App Store Connect API keys are not supported by `notarytool`.

Every migrated caller must configure a protected `release` environment with tag/branch restrictions and required reviewers. Keep signing values as organization/repository secrets and do not shadow them with same-named environment secrets. Serialize signed runs per repository and tag without cancelling notarization in progress.

GitHub resolves reusable workflows at job level with `jobs.<id>.uses`. A reusable file must live directly under `.github/workflows` and expose `on.workflow_call`. A full commit SHA is the safest immutable caller reference.

The caller's permissions can only reduce the reusable workflow's token permissions. Keep explicit least-privilege permissions in both the caller and shared workflow.

Run `validate_reusable_ci.py --require-signed-release <repo>` at the migration gate. This additionally proves the signed workflow pin and all six named secret mappings.

Centralization does not centralize dependency caches across repositories: GitHub Actions cache scope still includes repository boundaries. `sccache` improves repeat builds within each plugin repository, while path classification avoids unnecessary heavy jobs entirely.

Caller repositories also expose `plugin-install` configure/build/test presets for local macOS use. These presets inherit `plugin-release`; only the configure preset adds `EHL_COPY_PLUGIN_AFTER_BUILD=ON`. Reusable CI continues to use `plugin-release`, so macOS and Windows runners remain free of user-folder installation side effects.
