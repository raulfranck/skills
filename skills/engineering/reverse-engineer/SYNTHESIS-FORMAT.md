# System model format (provisional)

This format is a placeholder until the definitive report model is designed. Keep the section numbers stable so a later design can map onto them.

Write `synthesis/system-model.md` in the manifest's `report_language`. Every substantive sentence ends with the finding IDs it rests on, like `[A1-004]`. Match the wording to the certainty the digest shows: facts as plain statements, inferences as "likely", hypotheses as open possibilities, unknowns as questions.

1. **Summary**: what the system is, for whom, what it does and how it is shaped, in 5 to 10 lines.
2. **Context**: actors, external systems, the system boundary.
3. **Domain**: ubiquitous language (term table), bounded contexts and their classification (core, supporting, generic), key invariants, entity lifecycles.
4. **Architecture**: deployable units, modules and their dependencies, architectural style, declared versus actual (convergences, divergences, absences).
5. **Integrations and data**: interfaces exposed and consumed, sync versus async, contracts, sources of truth and ownership, consistency and idempotency.
6. **Critical flows**: one subsection per flow, with trigger, steps, state transitions, side effects and failure paths.
7. **Infrastructure and operations**: build and deploy path, environments, runtime topology, observability, resilience.
8. **Evolution**: hotspots, change coupling, knowledge distribution, milestones.
9. **Quality and risk**: prioritised risks with evidence, quality-attribute scenarios, trade-offs, technical debt worth knowing.
10. **Change guide**: for the 3 to 5 most likely changes (drawn from hotspots and focus questions), where to start, what else moves and what could break.
11. **Knowledge state**: counts by certainty, the unknowns that matter most and how to resolve each, and what stayed out of reach (runtime, repositories not in scope, people).
12. **Focus questions**: each question from the manifest, answered with IDs or marked open with what would answer it.

`synthesis/followups.md` lists up to 10 questions worth one more targeted pass. For each: the question, why it matters, the lens and scope that could answer it, and the evidence to look for.
