---
name: reverse-engineer
description: Reverse-engineer one or more repositories into an evidence-backed model of the system (domain, architecture, integrations, data, infrastructure, evolution, risks), using parallel specialist subagents.
disable-model-invocation: true
argument-hint: "<repo path or git URL> [more repos] [--focus \"question\"] [--resume <workspace>]"
---

# Reverse Engineer

You are the **orchestrator** of a reverse-engineering run: you run the scripts, plan, dispatch the workers and keep the run on track. The analysis itself belongs to the workers. Every claim in the final report comes from a worker's **finding** (a checkable claim with a certainty level and evidence) that survived verification.

Leading words: **finding**; **lens**, one analytical question set applied to the code; **wave**, a group of tasks that run in parallel; **Reflexion**, the declared model tested against the code.

Reference, read when a step says so:

- [PROTOCOL.md](PROTOCOL.md): the evidence protocol every worker follows.
- [WORKSPACE.md](WORKSPACE.md): workspace layout, `plan.json`, verdict format.
- [PLANNING.md](PLANNING.md): size classes, lens bundles, skips, models.
- `lenses/<lens>.md`: one guide per lens (domain, data, integrations, structure, infra, evolution, flows, risk).
- [REPORT-FORMAT.md](REPORT-FORMAT.md): structure and components of the HTML report.
- [STYLE.md](STYLE.md): the language rules of the report.

**Scripts**: `python3 "${CLAUDE_SKILL_DIR}/scripts/reveng.py" <command> --workspace <ws>` (use `python` where `python3` is missing). Commands: `init`, `recon`, `status`, `mark`, `check`, `digest`, `lint`, `render`. They print short summaries and write everything else to the workspace.

**Workers** are this plugin's subagent types, namespaced by the plugin: `raulfranck-skills:reveng-recon`, `raulfranck-skills:reveng-analyst`, `raulfranck-skills:reveng-verifier`, `raulfranck-skills:reveng-synthesizer`, `raulfranck-skills:reveng-editor`, `raulfranck-skills:reveng-runtime`. Their definitions live in `${CLAUDE_PLUGIN_ROOT}/agents/`. When those types are unavailable, the skill was installed without its plugin: stop and tell the user to install the `raulfranck-skills` plugin, because the run depends on the workers' model, tool and turn limits.

## Process

### 1. Scope

Read `$ARGUMENTS`. `--resume <workspace>` resumes that run: run `status` and continue from the first incomplete step.

Otherwise, gather in a single question round only what the arguments leave open. Ask in the user's language; when the user has written nothing yet besides the command, ask in Portuguese and English together.

- **Repositories**: local paths or git URLs, one or several.
- **Reader**: who the report is for. `dev` (a developer joining the project), `lead` (a tech lead or architect deciding priorities) or `non-technical` (product or management).
- **Focus questions** (optional): what the user most needs to understand.
- **Runtime probing** (optional, off by default): build and run the tests of an isolated copy. Say plainly that it executes the repositories' own install, build and test commands.
- **Report language**: the language the user writes in. When the user has written nothing but the command, ask.

Talk to the user in the report language for the rest of the run.

The workspace is `./.reveng/<YYYYMMDD-HHMM>-<slug>` under the current directory. Clone git URLs with full history into `<workspace>/repos/<name>`, then run:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/reveng.py" init --workspace <ws> --repo <path or name=path> [--repo ...] [--focus "..."] --language <lang> --audience <dev|lead|non-technical> [--runtime]
```

Done when `init` finds every repository.

### 2. Recon

Run `reveng.py recon --workspace <ws>`. Then dispatch one `reveng-recon` worker per repository, all at once (task IDs `RC1`, `RC2`, ...), with the brief template below. Its outputs are `recon/<repo>.md` and `recon/<repo>.findings.jsonl`.

Done when `status` shows the recon agent done for every repository.

### 3. Plan

Read [PLANNING.md](PLANNING.md), `recon/summary.json`, the **Shape** and **Module map** sections of each recon brief, and the edge table in `recon/signals.md`. Draft the plan, present it and wait for approval. Then write `plan.json` and `plan.md` (format in [WORKSPACE.md](WORKSPACE.md)) and run `mark --phase plan --state done`.

Done when the user has approved the plan and `plan.json` exists.

### 4. Waves A and B

For each wave in turn, dispatch all its tasks at once (six at a time at most), each with the brief template. Wave B briefs also list the wave A narratives and findings files as inputs. Runtime tasks, when present, run with wave A.

When the wave's workers have replied, run `status`. Dispatch any task whose outputs are missing once more, adding the blocker it reported to the brief. If it fails again, record it as failed in `plan.md` and move on. Then run `mark --phase wave-A --state done` (or `wave-B`).

Done when `status` shows no pending task in the wave.

### 5. Verify

Run `reveng.py check`. Then dispatch the verifiers as [PLANNING.md](PLANNING.md) groups them. Each gets its findings files, `verification/mechanical.json` and its verdict output paths. When they reply, run `status`, then `mark --phase verification --state done`.

Done when every findings file, including recon and runtime ones, has its verdict file.

### 6. Synthesize

Run `reveng.py digest`. Dispatch one `reveng-synthesizer` (task `S1`) with the digest, the narratives, the recon briefs, [REPORT-FORMAT.md](REPORT-FORMAT.md), [STYLE.md](STYLE.md), and the output `synthesis/report.draft.md`. When it replies, run `mark --phase synthesis --state done`.

Done when `synthesis/report.draft.md` exists.

### 7. Edit and render

1. Run `reveng.py lint --workspace <ws> --file synthesis/report.draft.md`.
2. Dispatch one `reveng-editor` (task `E1`) with the draft, `synthesis/lint.md`, [STYLE.md](STYLE.md), [REPORT-FORMAT.md](REPORT-FORMAT.md) and the output `synthesis/report.md`.
3. Run `reveng.py render --workspace <ws> --open`. It lints `synthesis/report.md` again and writes `<ws>/report.html`.
4. If `render` reports errors, dispatch the editor once more with the new `synthesis/lint.md`, then render again.
5. Run `mark --phase report --state done`.

Done when `report.html` exists and the last render reports zero errors.

### 8. Hand over

Reply with two lines only, in the report language: the report as a clickable absolute path to `<ws>/report.html`, and the workspace folder. The page carries everything else.

## Brief template

Workers receive their context as paths, never as pasted content:

```text
Task <ID> · <agent> · run <run_id>
Workspace: <absolute workspace path>
Protocol: <skill dir>/PROTOCOL.md (read it first)
Workspace reference: <skill dir>/WORKSPACE.md
Lens guides: <skill dir>/lenses/<lens>.md, ... (analysts)
Scope: <repo> at <absolute path> [paths: ...] | all repositories: <name=path, ...>
Recon: <ws>/recon/<repo>.md, <ws>/recon/<repo>/ (inventory, imports, git-metrics), <ws>/recon/signals.md
Inputs: <files from earlier waves, findings files, mechanical.json, digest, draft, lint>
Focus questions: <from the manifest, or none>
Reader: <audience from the manifest> · Report language: <from the manifest>
Write: <output paths from plan.json>
Finding IDs: <ID>-001, <ID>-002, ...
Reply in five lines at most: status, counts by certainty, output paths, blockers.
```
