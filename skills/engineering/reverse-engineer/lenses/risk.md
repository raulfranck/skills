# Lens: risk (wave B)

**Question**: which qualities does this system need, where are they at risk, and where would a change hurt most?

**Techniques**: ATAM, lightweight (quality-attribute scenarios, utility tree, sensitivity points, trade-offs, risks and non-risks); ISO/IEC 25010 as the vocabulary of quality attributes; STRIDE threat modelling over data flows and trust boundaries; hotspot-prioritised technical debt (Tornhill); failure mode analysis.

**Start from**: every wave A and flows narrative and findings file listed in your brief; the recon hotspots and change coupling; the integrations trust findings; the infra resilience findings.

## Procedure

1. **Quality attributes.** From the domain and operations evidence, infer the 3 to 5 attributes that matter most (availability, data integrity, performance, security, modifiability, cost), and why.
2. **Scenarios.** Write 5 to 10 quality-attribute scenarios (source, stimulus, environment, response, measure), each tied to evidence of how the current design responds.
3. **Risks.** For each risk: what could go wrong, where, the evidence, and the reasoning behind its likelihood and impact. Add the sensitivity points (one decision that drives an attribute) and trade-offs (one decision that pulls two attributes in opposite directions). Record non-risks too: concerns the design handles well.
4. **Threats.** Walk STRIDE over each trust boundary in the flows (spoofing, tampering, repudiation, information disclosure, denial of service, elevation of privilege), recording only threats the code gives evidence for.
5. **Debt worth knowing.** Intersect hotspots, complexity and business criticality. Debt in a cold, stable module is cheap; debt in a hot core module is expensive.
6. **Change danger map.** The modules or files where a change is riskiest, and why: many dependents, hidden coupling, missing tests, a single knowledge holder, a critical flow.

Every risk traces to at least one fact from this task or an earlier wave (use `based_on`). Advice that has no evidence in this codebase has no place in the findings.

## Kinds

`quality-attribute`, `quality-scenario`, `risk`, `non-risk`, `sensitivity-point`, `tradeoff`, `threat`, `debt`, `change-risk`, `note`

## Narrative outline

Quality attributes that matter · Scenarios · Top risks (table: risk, finding IDs, likelihood, impact) · Threats per boundary · Debt worth knowing · Change danger map · Non-risks · Open questions
