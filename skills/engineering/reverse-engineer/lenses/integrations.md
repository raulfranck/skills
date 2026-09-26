# Lens: integrations

**Question**: where are the system's boundaries, and how does it talk across them?

**Techniques**: context mapping (customer/supplier, conformist, anti-corruption layer, open host service, published language, shared kernel); architecture recovery for distributed systems (topology from configuration, deployment descriptors and contracts); follow the network: every URL, topic, queue and client.

**Start from**: `recon/signals.md` (exposed routes, outbound hosts, endpoint environment variables, messaging names, contracts, compose and Kubernetes objects, candidate cross-repository edges); HTTP, gRPC and SDK client code; producers and consumers; authentication middleware.

## Procedure

1. **Exposed surface.** APIs grouped by resource, events published, files or exports produced, command-line entry points. Contract documents (OpenAPI, protobuf, AsyncAPI, GraphQL) and whether the code matches them.
2. **Consumed surface.** Every outbound dependency: internal services, third-party APIs (payments, email, identity), cloud services. Record direction, style (synchronous request, asynchronous message, batch file, shared database) and purpose.
3. **Candidate edges.** Confirm or refute each candidate edge from `signals.md` by reading the code on both sides. An edge you cannot settle stays a hypothesis with `how_to_verify`. Done when every candidate edge has a finding.
4. **Messaging topology.** For each topic or queue: producers, consumers, payload type, and delivery assumptions (ordering, at-least-once handling).
5. **Context map.** The relationship pattern between contexts or services: who adapts to whom, where anti-corruption layers sit, which models are shared.
6. **Boundary resilience.** Timeouts, retries, circuit breakers, fallbacks and bulkheads on each outbound call. A critical call without them is a high-impact finding.
7. **Trust.** How callers authenticate and are authorised at each boundary: tokens, mTLS, API keys (by variable name), or nothing.

## Kinds

`interface-exposed`, `dependency`, `edge`, `contract`, `topic`, `context-relation`, `resilience`, `auth`, `external-system`, `note`

## Narrative outline

System boundary (actors and external systems) · Exposed interfaces · Dependencies (table: from, to, style, purpose, resilience) · Messaging topology · Context map · Trust at the boundaries · Open questions
