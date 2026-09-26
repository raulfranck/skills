# Lens: data

**Question**: where does the system's state live, who owns it, and how does it stay consistent?

**Techniques**: Analyze the Persistent Data (Object-Oriented Reengineering Patterns): the schema as the most honest model of the business; data ownership per bounded context; consistency patterns (transactions, outbox, saga, compensation, eventual consistency); idempotency; cache-aside and invalidation; data lifecycle and privacy.

**Start from**: the inventory's data section (migrations, SQL, schema files) and ORM hints; ORM models and repositories; transaction boundaries (`@Transactional`, `BEGIN`/`COMMIT`, unit of work); message handlers (deduplication, retries); cache clients; datastore configuration in compose and IaC; retention and cleanup jobs; fields that hold personal data.

## Procedure

1. **Stores.** Every datastore (relational and document databases, caches, object storage, search indexes, queues used as storage, files): technology, what it holds, which deployable unit connects to it. Done when every datastore the recon found has a `store` finding.
2. **Model.** The main tables or collections and their relationships, and which of them carry status (these feed the domain lens's lifecycles).
3. **Ownership.** For each core entity, its source of truth and every writer. Tables written by several modules or services are high-impact findings. Done when every core entity has an `ownership` finding.
4. **Consistency.** Transaction boundaries on the main write paths. Writes that span stores or services, and how they stay consistent (outbox, saga, retries, or nothing). Read-after-write assumptions.
5. **Idempotency and duplicates.** Idempotency keys, unique constraints, consumer deduplication, and the places where a retry would repeat an effect.
6. **Caching.** What is cached, under which keys, with which TTL and invalidation, and where stale reads could hurt.
7. **Lifecycle and privacy.** Retention, soft versus hard delete, archival, backups. Personal and sensitive fields (by name) and how they are protected.

## Kinds

`store`, `schema`, `ownership`, `shared-data`, `transaction`, `consistency`, `idempotency`, `cache`, `data-lifecycle`, `pii`, `note`

## Narrative outline

Stores · Model (main entities and relations) · Ownership map (entity, source of truth, writers) · Consistency and idempotency · Caching · Lifecycle and privacy · Open questions
