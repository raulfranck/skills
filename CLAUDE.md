Skills library for coding agents, organised by area and shipped as a single Claude Code plugin named `raulfranck-skills`, so every skill is invoked as `/raulfranck-skills:<skill>` and every worker is typed `raulfranck-skills:<agent>`.

Language: human-facing text (`README.md`, `docs/`, bucket READMEs, marketplace and plugin descriptions) is written in Brazilian Portuguese. Agent-facing text (`SKILL.md`, agents, reference files, `CLAUDE.md`, `CONTEXT.md`, `.agents/`) is written in English.

## Layout

- The repository root is the plugin root: `.claude-plugin/plugin.json` is the plugin, and `.claude-plugin/marketplace.json` is a one-entry marketplace pointing at `./`. See [ADR 0001](.agents/adr/0001-one-plugin-for-the-repository.md).
- `skills/<area>/<skill>/` holds `SKILL.md`, UPPERCASE reference files beside it, and `scripts/` for deterministic helpers. Each area (today `engineering`) is listed in `plugin.json`'s `skills` array, so every skill folder inside it ships.
- `agents/` holds the subagents that skills dispatch, flat, each prefixed by its owning skill.
- Lifecycle buckets are never listed in `plugin.json` and never ship: `skills/in-progress/` (beta), `skills/misc/` (kept, rarely used), `skills/deprecated/` (retired).
- `docs/<area>/<skill>.md` is the human docs page of each shipped skill; follow [.agents/writing-docs.md](.agents/writing-docs.md).
- `.agents/` holds maintainer references and ADRs. `.out-of-scope/` holds one file per request deliberately declined.

## Invariants

- Every area folder is listed in `plugin.json` as `./skills/<area>/`; lifecycle buckets never are.
- A skill always sits inside an area (`skills/<area>/<skill>/SKILL.md`), never directly under `skills/`: the default scan would ship it.
- Every shipped skill has a line in the top-level `README.md` and in its area `README.md` (under **User-invoked** or **Model-invoked**), and a docs page.
- Subagents live flat in `agents/`, named with a prefix owned by their skill (`reveng-` for `reverse-engineer`). Their `description` says which skill dispatches them, and their `tools` list leaves out `Agent` and `Skill`. Subfolders under `agents/` do not load. See [ADR 0002](.agents/adr/0002-subagents-in-the-plugin-agents-folder.md).
- Frontmatter values containing `: ` must be quoted, or the whole frontmatter is ignored (an agent would then lose its tool and model limits).
- Neither `plugin.json` nor the marketplace entry sets `version`: every commit on the default branch is a release. Record user-visible changes in `CHANGELOG.md`. See [ADR 0004](.agents/adr/0004-releases-follow-commits.md).
- The plugin `name` is permanent: renaming it breaks every existing install.
- Every other plugin component at the root (`commands/`, `hooks/`, `bin/`, `.mcp.json`, `settings.json`) ships to every user; add one only on purpose.
- Invocation follows [.agents/invocation.md](.agents/invocation.md).
- Scripts are Python 3.9+ standard library only and run on Windows, macOS and Linux.

## Checks

Run both after touching a manifest, or adding, moving or renaming a skill or agent:

```bash
claude plugin validate .
python scripts/check-repo.py
```

`claude plugin validate --strict` fails by design here, because releases carry no `version`.

## Writing

Agent-facing text follows these principles: leading words that recruit the model's priors, a clear completion criterion on every step, progressive disclosure (reference in separate files, reached by pointer), positive instructions rather than prohibitions, one source of truth for each meaning, and no sentence that only restates default behaviour.
