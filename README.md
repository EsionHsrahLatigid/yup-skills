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

## Included skills

- `yup-build-plugin`: build, test, locate, and verify the stable `artifacts/` product tree.
- `yup-ci-maintainer`: adopt and validate the reusable macOS/Windows CI and exact-SHA release workflows from `EsionHsrahLatigid/yup-actions`.

## License

MIT.
