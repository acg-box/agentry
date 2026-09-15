# AGENTS

## Repository

This repository publishes ACG Box engineering standards as small Codex plugins.
Use [OpenWiki quickstart](openwiki/quickstart.md) for repository navigation. Read
the owning skill and relevant canonical sections when changing runtime guidance.

## Authority

- `plugins/` contains installable runtime guidance.
- `.agents/plugins/marketplace.json` contains the marketplace entry.
- `VERSION` and each plugin manifest must use the same release version.
- `openwiki/` contains repository context and maintainer operations. It does not
  replace plugin runtime authority.
- Add `dev/` only when a real test, benchmark, evaluation, fixture, or maintainer
  reference needs an owner.
- Do not add `apps/` or `packages/` until this repository owns an application or
  reusable software package.

## Work

- Keep the primary worktree on `main`. Use `.worktrees/<task>` for changes.
- Use the plugin and skill creation workflows for manifests, marketplace entries,
  skills, and `agents/openai.yaml`.
- Keep one canonical standard. Link to it instead of copying its rules into
  OpenWiki or the README.
- Skills supply team policy, non-obvious constraints, and completion criteria.
  Leave general implementation, troubleshooting, and test selection to the model.
- Run `cargo make check`, the Plugin Creator validator, and the Skill Creator
  validator before a ready claim.
- For durable workflow or layout changes, update source authority first. Then run
  `openwiki code --update --print` and review all proposed OpenWiki and `AGENTS.md`
  changes. Curate directly when generation cannot preserve the repository's small
  ownership model.
- Do not install, publish, push, or release unless the user requests it.
