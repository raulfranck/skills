# Lens: structure

**Question**: how is the code organised, how do its parts depend on each other, and does that match the architecture it claims?

**Techniques**: Reflexion models (Murphy, Notkin, Sullivan): compare the declared model with the extracted one and classify every relation as convergence, divergence or absence; dependency structure analysis (Martin's afferent and efferent coupling and instability, cycles); Study the Exceptional Entities (Object-Oriented Reengineering Patterns); C4-style zoom from deployable units to components; coupling and cohesion (connascence).

**Start from**: `recon/<repo>/imports.md` (modules, edges, Ca, Ce, instability, cycles, parser coverage); the inventory's modules and largest files; the recon brief's declared-architecture hypotheses; docs and ADRs; build files, which draw module and project boundaries; dependency-injection setup and composition roots.

## Procedure

1. **Deployable units and components.** What is built and deployed separately, and the main components inside each.
2. **Declared model.** From docs, ADRs, folder names and naming conventions: the intended layers or modules and their allowed dependencies. Reuse the recon's hypotheses and add the ones it missed.
3. **Extracted model.** The actual module dependencies, from `imports.md` confirmed by spot checks in the code. Where parser coverage is low, or dependency injection and reflection hide the wiring, read the composition roots.
4. **Reflexion.** For each declared rule, record a convergence (it holds), a divergence (a dependency the declared model forbids, quoting the import) or an absence (an expected dependency that does not exist). Done when every declared-architecture hypothesis ends in one of the three.
5. **Cycles and coupling.** Explain each cycle: which concept pulls the modules together. Name the modules with high afferent coupling (many dependents, so changes ripple) and high efferent coupling (many dependencies, so they break easily).
6. **Exceptional entities.** The five largest or most complex files and any god module: what they do and why they grew.
7. **Style.** The architectural styles actually present (layered, hexagonal, MVC, modular monolith, microservices, event-driven), with evidence.

## Kinds

`deploy-unit`, `component`, `module`, `layer-rule`, `convergence`, `divergence`, `absence`, `cycle`, `coupling`, `exceptional-entity`, `style`, `note`

## Narrative outline

Deployable units · Declared versus actual (Reflexion table) · Module dependencies and cycles · Exceptional entities · Architectural style · Open questions
