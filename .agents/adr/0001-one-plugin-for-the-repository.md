# One plugin for the whole repository, named raulfranck-skills

Claude Code namespaces every skill and agent under the plugin's manifest name: a skill runs as `/<plugin>:<skill>` and a worker is typed `<plugin>:<agent>`. The library wants one recognisable namespace for all its skills, whatever area they belong to: `/raulfranck-skills:<skill>`.

## Decision

- The repository root is the plugin root. `.claude-plugin/plugin.json` names the plugin `raulfranck-skills`.
- `.claude-plugin/marketplace.json` makes the repository its own marketplace, named `raulfranck`, with one entry whose `source` is `"./"`. Users install `raulfranck-skills@raulfranck`.
- Areas are folders under `skills/`, each listed in `plugin.json`'s `skills` array as `./skills/<area>/`. Lifecycle buckets (`in-progress/`, `misc/`, `deprecated/`) stay unlisted and never ship.
- Subagents sit in the root `agents/` folder ([ADR 0002](0002-subagents-in-the-plugin-agents-folder.md)).

## Alternatives rejected

- **One plugin per area** (`engineering`, ...): the namespace would be the generic area name (`/engineering:reverse-engineer`), easy to collide with other authors' plugins, and users would install each area separately.
- **Plugin root in a subfolder**: separates the plugin from the repository's docs and checks for no gain.

## Consequences

- Every user loads the descriptions of every shipped skill and agent in every session. Keep descriptions short, and move rarely used skills to `misc/`.
- The plugin name is permanent: renaming it breaks every install.
- Development loop without installing: `claude --plugin-dir .`.
