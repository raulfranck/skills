# Planning

Turn the recon metrics into the smallest set of tasks that still covers every lens with evidence. Cost grows with agent runs, so bundle lenses whose evidence overlaps and split only where one worker could not cover the ground in its turn budget.

The bundles below are the plan, not a suggestion. A focus question changes what the tasks look at, never how many there are. Split a bundle only when the user asks for it at the approval step.

## Inputs

- `recon/summary.json`: per repository, non-test source LOC, modules, languages, commits and history depth, IaC, CI, contracts, migrations, routes, messaging names.
- The recon briefs' **Shape** and **Module map** sections.
- `recon/signals.md`: the candidate cross-repository edges table.
- The focus questions in the manifest.

## Size class

Per repository, by non-test source LOC:

| Class | Source LOC |
|---|---|
| S | under 20k |
| M | 20k to 150k |
| L | 150k to 600k |
| XL | over 600k |

## Lens bundles

Wave A holds the independent lenses; wave B holds `flows` and `risk`, which read wave A's output.

**One repository:**

| Class | Wave A | Wave B |
|---|---|---|
| S | [domain, data, integrations] · [structure, infra, evolution] | [flows, risk] |
| M | [domain, data] · [integrations] · [structure] · [infra, evolution] | [flows] · [risk] |
| L | [domain, data] per module group · [integrations] · [structure] · [infra] · [evolution] | [flows] ×2 (split the chosen flows) · [risk] |
| XL | Ask the user to narrow the scope (modules, or focus questions) before planning, then plan the narrowed scope as L. | |

A **module group** is a set of modules from `inventory.json` that share a top directory or package and hold roughly 50k to 100k LOC. Pass the group as the task's `paths`.

**Several repositories:**

- Per repository, its local lenses by class: [domain, data], [structure], [infra, evolution]. For an S repository, bundle all of them into one task.
- One cross-repository [integrations] task over all repositories (split into clusters of connected repositories above 6 repositories).
- Wave B: cross-repository [flows] (one task per 4 flows) and one system-wide [risk].

## Skips

Record each skip in `plan.json` under `skipped`, with its reason:

- **evolution**: fewer than 20 commits or shallow history. The synthesis reports it as unknown.
- **infra**: no IaC, CI or Dockerfile. Fold a short infra check into the structure task instead.
- **integrations** (one repository): no routes, outbound hosts, messaging names or contracts. Fold it into the domain task.
- **runtime**: only when `manifest.runtime_opt_in` is true. One `reveng-runtime` task per repository, in wave A.

## Models

- Recon: haiku (agent default). Analysts, runtime, verifiers and the editor: sonnet. Synthesizer: opus.
- Propose opus for the risk task when the system is L or XL, or when the focus questions are about risk, and say why. The user decides.

## Verification

One verifier per group of up to 5 findings files, all in parallel: a single verifier for an S run. Include the recon and runtime findings files.

## Concurrency

Dispatch at most 6 workers at a time and queue the rest.

## Presenting the plan

Show a compact table: each wave with its tasks (ID, lenses, scope, model), total agent runs by model (recon, analysts, verifiers, synthesizer and editor), skipped lenses with reasons, and a rough wall time (5 to 15 minutes per wave). An S run is 7 agent runs: 1 recon, 3 analysts, 1 verifier, 1 synthesizer, 1 editor. Ask for approval: the user may trim, merge or add tasks. Write `plan.json` and `plan.md` after approval.

These thresholds are a starting point. Calibrate them after pilot runs and record the change here.
