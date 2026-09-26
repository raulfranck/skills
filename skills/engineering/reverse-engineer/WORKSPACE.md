# Workspace

One directory per run, created by `reveng.py init`. Everything a run produces lives here, and the analysed repositories stay untouched.

```text
<workspace>/
├── manifest.json              run identity, repositories (path, HEAD, history), language, focus, phase status
├── plan.json · plan.md        the approved plan
├── inputs/scope.md            what the user asked for
├── repos/                     clones of repositories given as URLs
├── recon/
│   ├── summary.json           per-repo metrics for planning
│   ├── signals.json · .md     integration signals and candidate cross-repo edges
│   ├── <repo>/                inventory · imports · git-metrics (.json and .md, from scripts)
│   └── <repo>.md · <repo>.findings.jsonl        recon brief and findings (recon agent)
├── lenses/<task>-<lenses>--<scope>.md · .findings.jsonl     analysts
├── runtime/<repo>.md · <repo>.findings.jsonl                 runtime agent (opt-in)
├── verification/
│   ├── mechanical.json · .md  evidence check (script)
│   └── <task>.verdicts.jsonl  verifiers, one file per findings file
├── synthesis/
│   ├── digest.json · .md      findings merged with checks and verdicts (script)
│   ├── synthesis.findings.jsonl   findings added while synthesising
│   ├── report.draft.md        synthesizer
│   ├── report.md              editor
│   └── lint.json · .md        language and structure check (script)
└── report.html                the final report (script: render)
```

## plan.json

```json
{
  "run_id": "20260925-1430-billing",
  "waves": [
    {"wave": "A", "tasks": [
      {"id": "A1", "agent": "reveng-analyst", "model": "sonnet", "lenses": ["domain", "data"],
       "repo": "billing", "paths": [],
       "outputs": {"narrative": "lenses/A1-domain-data--billing.md",
                   "findings": "lenses/A1-domain-data--billing.findings.jsonl"}},
      {"id": "R1", "agent": "reveng-runtime", "repo": "billing",
       "outputs": {"narrative": "runtime/billing.md", "findings": "runtime/billing.findings.jsonl"}}
    ]},
    {"wave": "B", "tasks": [
      {"id": "B1", "agent": "reveng-analyst", "lenses": ["flows"], "repo": "*",
       "inputs": ["lenses/A1-domain-data--billing.md", "lenses/A1-domain-data--billing.findings.jsonl"],
       "outputs": {"narrative": "lenses/B1-flows--all.md", "findings": "lenses/B1-flows--all.findings.jsonl"}}
    ]},
    {"wave": "V", "tasks": [
      {"id": "V1", "agent": "reveng-verifier",
       "inputs": ["lenses/A1-domain-data--billing.findings.jsonl", "lenses/B1-flows--all.findings.jsonl"],
       "outputs": {"verdicts": ["verification/A1.verdicts.jsonl", "verification/B1.verdicts.jsonl"]}}
    ]},
    {"wave": "S", "tasks": [
      {"id": "S1", "agent": "reveng-synthesizer", "model": "opus",
       "outputs": {"draft": "synthesis/report.draft.md"}},
      {"id": "E1", "agent": "reveng-editor",
       "outputs": {"report": "synthesis/report.md", "html": "report.html"}}
    ]}
  ],
  "skipped": [{"lens": "evolution", "repo": "billing", "reason": "shallow history"}]
}
```

- `id` doubles as the finding ID prefix: `A*` wave A, `B*` wave B, `R*` runtime (runs with wave A), `V*` verification, `S1` synthesis, `E1` editing. Recon tasks use `RC1`, `RC2`, ... and are not part of the plan.
- `repo` is a repository name, or `*` for a task that spans all repositories. `paths` narrows a partitioned task to module prefixes.
- `model` overrides the agent's default model; omit it to keep the default.
- `inputs` lists extra workspace files the task reads; `outputs` lists every file the task must write.

`reveng.py status` counts a task as done when all its outputs exist and are non-empty. Resuming a run means dispatching the tasks `status` lists as pending.

## Verdict lines

One JSON object per line in `verification/<task>.verdicts.jsonl`, where `<task>` is the task that wrote the findings file (`A1` for `lenses/A1-...findings.jsonl`, `RC1` for `recon/<repo>.findings.jsonl`, `R1` for `runtime/<repo>.findings.jsonl`):

```json
{"id": "A1-004", "verdict": "downgraded", "certainty": "hypothesis", "reason": "ISSUED may be set by a database trigger"}
{"id": "A1-002", "verdict": "relocated", "reason": "enum is at lines 3-8", "evidence": [{"repo": "billing", "path": "src/invoices/invoice.entity.ts", "lines": "3-8", "quote": "export enum InvoiceStatus {"}]}
```

`verdict` is one of `confirmed`, `downgraded` (with the new `certainty`), `refuted`, `relocated` (with corrected `evidence`) or `unverifiable`.
