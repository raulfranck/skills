# Lens: flows (wave B)

**Question**: what actually happens, end to end, when the system does the things that matter most?

**Techniques**: use-case driven tracing; Step Through the Execution (Object-Oriented Reengineering Patterns), done statically; feature location; control-flow and data-flow following across process boundaries; failure-path analysis.

**Start from**: the wave A narratives and findings listed in your brief (domain: core entities, lifecycles, invariants; integrations: interfaces and edges; data: ownership); the recon entry points; the focus questions.

## Procedure

1. **Choose the flows.** Pick 3 to 6: core-domain commands, paths that move money or make decisions, flows that cross the most boundaries, and every flow a focus question points at. Record one `flow` finding per choice with the reason. Done when each focus question maps to a flow or is recorded as out of reach.
2. **Trace each flow** from its trigger (route, consumer, job, UI action) to its last side effect: entry, validation, domain logic, persistence, events, downstream consumers, external calls. Cite every hop. Where the trail leaves the repositories in scope, record the boundary and what is expected beyond it.
3. **State.** The lifecycle transitions each flow performs.
4. **Failure paths.** For each flow, at least the two most likely failures (a dependency down, invalid input, duplicate delivery, a partial write) and what the code does: retry, compensate, fail, or leave data inconsistent. Done when every flow has at least one failure path recorded.
5. **Side effects.** Emails, payments, external writes, events: which are idempotent and which could happen twice.

## Kinds

`flow`, `flow-step`, `side-effect`, `failure-path`, `boundary`, `note`

## Narrative outline

One section per flow: trigger · step table (hop, where, finding IDs) · state transitions · failure paths · side effects. Then cross-flow observations · Open questions
