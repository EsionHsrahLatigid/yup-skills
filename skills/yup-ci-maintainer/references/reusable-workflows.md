# Reusable YUP workflow contract

Canonical repository: `https://github.com/EsionHsrahLatigid/yup-actions`

Reusable files:

- `.github/workflows/plugin-ci.yml`
- `.github/workflows/plugin-release.yml`

The CI caller provides:

- `product_name`
- `product_slug`
- `cmake_option_prefix`
- `debug_targets_json`
- `release_test_targets_json`
- `windows_debug_plugins`
- `force_heavy`

The release caller provides `product_name` and grants `actions: read` plus `contents: write`.

GitHub resolves reusable workflows at job level with `jobs.<id>.uses`. A reusable file must live directly under `.github/workflows` and expose `on.workflow_call`. A full commit SHA is the safest immutable caller reference.

The caller's permissions can only reduce the reusable workflow's token permissions. Keep explicit least-privilege permissions in both the caller and shared workflow.

Centralization does not centralize dependency caches across repositories: GitHub Actions cache scope still includes repository boundaries. `sccache` improves repeat builds within each plugin repository, while path classification avoids unnecessary heavy jobs entirely.
