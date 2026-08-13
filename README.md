# yup-skills

Codex skills for building and maintaining EHL audio plugins based on YUP.

## Install with the skills CLI

```sh
npx skills add EsionHsrahLatigid/yup-skills \
  --skill yup-build-plugin \
  --skill yup-ci-maintainer \
  --global --agent codex --yes
```

The repository follows the `skills/<name>/SKILL.md` discovery convention used by the skills CLI.

Current `skills` CLI releases keep the global canonical copy under `~/.agents/skills/` even when `--agent codex` is selected; Codex lists and loads that location. Environments that require a literal `~/.codex/skills/<name>` path can add a compatibility symlink to the canonical copy.

## Included skills

- `yup-build-plugin`: build, test, locate, install, and verify the stable `artifacts/` tree plus local macOS VST3/AU copies.
- `yup-ci-maintainer`: adopt and validate the reusable macOS/Windows CI and exact-SHA release workflows from `EsionHsrahLatigid/yup-actions`.

## License

MIT.
