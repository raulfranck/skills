# reverse-engineer: generic analyst, lens guides, evidence protocol and a deterministic backbone

Analysing one or many repositories in a single agent session overflows the context window and invites invented architecture. The skill splits the work across workers, and four choices shape how.

## Decision

1. **Five workers, not one per lens.** `reveng-recon` (haiku), `reveng-analyst` (sonnet), `reveng-verifier` (sonnet), `reveng-synthesizer` (opus) and `reveng-runtime` (sonnet, opt-in). The analyst is generic; what it analyses comes from the lens guides named in its brief.
2. **Lens knowledge lives in `lenses/<lens>.md`.** Each guide is the single source of truth for its lens and loads only in the analysts that apply it. Planning can therefore bundle lenses whose evidence overlaps into one task (cheaper on small repositories) or split one lens across module groups (large ones) without new agent definitions.
3. **Findings with certainty, checked twice.** Workers write JSON-line findings (fact, inference, hypothesis, unknown) with quoted evidence. A script checks every citation mechanically; an independent verifier judges semantic support for the findings that matter; the digest drops refuted findings and downgrades weak ones before synthesis.
4. **Scripts do the counting.** Inventory, module dependencies, git behaviour (hotspots, change coupling, knowledge), integration signals, evidence checks and the digest are deterministic Python: free, repeatable, and exact where models estimate.

The orchestrator stays thin. It passes paths rather than content, never analyses code itself, and shows the user the plan (agent runs by model) before spending on analysis.

## Alternatives rejected

- **One agent definition per lens**: ten always-loaded descriptions, and no way to bundle lenses for small repositories.
- **A single analysing agent**: context overflow on real systems, and no independent check of its claims.
- **Model-computed metrics**: churn, coupling and dependency counts drift between runs and cannot be verified.

## Consequences

- Size thresholds and bundles in `PLANNING.md` are first guesses; calibrate them after pilot runs.
- The report format (`SYNTHESIS-FORMAT.md`) is provisional and will be designed separately. Section numbers stay stable so a new design can map onto them.
