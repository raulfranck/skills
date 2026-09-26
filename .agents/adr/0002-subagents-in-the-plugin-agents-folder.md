# Subagents live flat in the plugin's agents folder

`reverse-engineer` needs more than a subagent brief written inside its `SKILL.md`: each worker has its own model, tool list, turn limit and effort, which only a Claude Code subagent definition provides.

Tested on Claude Code 2.1.270 with `claude plugin details`:

| Where the agent file sits | Loaded |
|---|---|
| `agents/<name>.md` at the plugin root | yes |
| `agents/<subfolder>/<name>.md` | no |
| a path listed in the manifest's `agents` array outside `agents/` | no |

## Decision

- Subagents live flat in the root `agents/` folder.
- Each file name and `name` carries a prefix owned by its skill (`reveng-` for `reverse-engineer`), so the folder can hold the workers of many skills without collisions.
- The `description` says which skill dispatches the worker, so the main agent does not borrow it for unrelated work. Descriptions stay short: each one is loaded in every session.
- The `tools` list leaves out `Agent` and `Skill`. A worker therefore cannot re-invoke its skill and fan out into more and more agents.
- `omitClaudeMd: true` when the worker does not need the host project's `CLAUDE.md`, which saves tokens on every dispatch.

## Consequences

- A skill's workers sit outside its folder; the skill refers to them by type (`raulfranck-skills:<name>`).
- A skill that depends on its workers only works when installed through the plugin, and it says so when the worker types are missing.
- Revisit when subfolders under `agents/` load: `agents/<skill>/<role>.md` would group workers by skill for free.
