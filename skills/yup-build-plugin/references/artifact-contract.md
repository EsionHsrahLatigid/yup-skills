# EHL YUP artifact contract

The stable consumer surface is:

```text
artifacts/
└── plugin-release/
    └── <platform-arch>/
        ├── standalone/
        ├── vst3/
        ├── au/              # macOS only
        └── ARTIFACTS.txt
```

Expected platform keys are `macos-arm64` and `windows-x64` in GitHub Actions. Local builds may use another architecture key.

`ARTIFACTS.txt` records product, profile, platform, configuration, and format names. It is evidence about the staged copy, not a substitute for tests or signature verification.

For local macOS builds outside CI, the same `ehl_stage_products` target physically copies the staged plugin bundles to:

```text
~/Library/Audio/Plug-Ins/
├── VST3/<slug>_vst3_plugin.vst3
└── Components/<slug>_au_plugin.component
```

The target replaces only those exact bundle paths. It does not install the Standalone application, delete unrelated plugins, or create symlinks. `ARTIFACTS.txt` records `installed_vst3` and `installed_au` paths when copying is enabled. CI, Windows, and explicit `-DEHL_COPY_PLUGIN_AFTER_BUILD=OFF` builds only refresh `artifacts/`. `EHL_USER_VST3_DIR` and `EHL_USER_AU_DIR` can redirect local copies.

The repository owns a vendored copy of:

- `cmake/EhlYupArtifactLayout.cmake`
- `cmake/StageYupProducts.cmake`

`CMakeLists.txt` registers one common target named `ehl_stage_products`. The `plugin-release` build preset includes that target, so normal preset builds refresh the stable output automatically.

The canonical source is `EsionHsrahLatigid/yup-actions`. Vendoring keeps local builds offline-capable and makes each plugin commit reproducible. Update vendored helpers intentionally and validate a real Standalone, VST3, and AU build before rollout.
