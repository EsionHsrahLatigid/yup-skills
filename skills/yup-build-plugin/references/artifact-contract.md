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

The repository owns a vendored copy of:

- `cmake/EhlYupArtifactLayout.cmake`
- `cmake/StageYupProducts.cmake`

`CMakeLists.txt` registers one common target named `ehl_stage_products`. The `plugin-release` build preset includes that target, so normal preset builds refresh the stable output automatically.

The canonical source is `EsionHsrahLatigid/yup-actions`. Vendoring keeps local builds offline-capable and makes each plugin commit reproducible. Update vendored helpers intentionally and validate a real Standalone, VST3, and AU build before rollout.
