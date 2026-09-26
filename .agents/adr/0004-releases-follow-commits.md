# Releases follow commits

Claude Code decides whether an installed plugin has an update by comparing versions. It takes the version from `plugin.json` first, then from the marketplace entry. When neither sets one, a plugin in a git-hosted marketplace gets the commit SHA of its directory as its version.

A pinned `version` that nobody bumps keeps every user on the old copy, however many commits land.

## Decision

Neither `plugin.json` nor the marketplace entry sets `version`. Every commit on the default branch is a release, and users receive it through auto-update (once they turn it on for the `raulfranck` marketplace) or `claude plugin update raulfranck-skills@raulfranck`.

## Consequences

- Work happens on branches; merging into the default branch is releasing.
- `claude plugin validate --strict` warns about the missing version, so the checks run without `--strict`.
- User-visible changes go in `CHANGELOG.md` by date.
- If a semantic release flow becomes necessary (for a directory listing, or for plugins that depend on this one), add `version` to `plugin.json` and bump it on every release, ideally from CI.
