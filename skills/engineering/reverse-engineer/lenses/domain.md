# Lens: domain

**Question**: what problem does the system solve, in whose language, under which rules?

**Techniques**: DDD strategic design (ubiquitous language, bounded contexts, core, supporting and generic subdomains); Event Storming in reverse (events, commands, aggregates and policies read out of the code); aggregate invariants and Design by Contract; entity life histories (state machines).

**Start from**: the recon brief's domain reading list. Then entity, model and domain folders; enums and status fields; validations and guard clauses; domain exceptions and error messages; event and command names; route names; migrations and database constraints; test names, which state intended behaviour; UI strings and translation files.

## Procedure

1. **Purpose and actors.** Test the recon's purpose hypothesis against routes, roles and permissions, and core entities. Record the actors: user roles, operators, external systems acting on this one. Done when the purpose hypothesis is confirmed, refuted or refined with evidence.
2. **Language.** Harvest the terms the code uses for business concepts (entities, events, commands, statuses): what each means as the code enacts it, and where it lives. Flag synonyms (two names for one concept) and homonyms (one name with two meanings across modules): both mark context boundaries. Done when every core entity has a `term` finding.
3. **Contexts.** Group terms by the modules that own them and the data they write. Name each bounded context and classify it: core (the differentiator, where most rules and change live), supporting, or generic (commodity: identity, notifications, a payment provider wrapper), with reasoning. Done when every module belongs to a context or is marked technical.
4. **Invariants.** Find the rules the code defends: guards, validations, database constraints (CHECK, UNIQUE, foreign keys), domain exceptions. One finding per rule, quoting the guarding code. Note rules enforced twice, or only in the UI. Done when each context's key entities have their rules recorded, or an explicit finding that none were found.
5. **Lifecycles.** For each entity with a status or state field: states, transitions, the trigger of each transition (who, or which event), guards, terminal states, what a failure in mid-transition leaves behind, and whether a transition can safely repeat. A transition that no code performs is a high-impact finding: it happens elsewhere, or never. Done when every status field is covered.
6. **Events and policies.** Domain events emitted and consumed, and the "when X happens, do Y" policies that react to them.

## Kinds

`purpose`, `actor`, `term`, `context`, `subdomain`, `capability`, `invariant`, `lifecycle`, `transition`, `event`, `policy`, `note`

## Narrative outline

Purpose and actors · Ubiquitous language (table: term, meaning, where) · Contexts and their classification · Invariants · Lifecycles (one state table per entity) · Events and policies · Open questions
