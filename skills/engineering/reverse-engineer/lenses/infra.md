# Lens: infra

**Question**: how does the code become running software, and how is it operated?

**Techniques**: the deployment view (4+1 physical view, C4 deployment diagrams as a mental model); the Four Golden Signals and the RED and USE methods to judge observability; production-readiness review; failure mode analysis.

**Start from**: the inventory's IaC, CI, configuration and observability sections; Dockerfiles, compose files, Kubernetes and Helm manifests, Terraform, CDK and serverless files; CI workflows; environment templates; logging, metrics and tracing setup; health checks; runbooks.

## Procedure

1. **Pipeline.** From commit to artifact to deployment: CI stages, which tests run, the artifact type and registry, the deploy mechanism, promotion between environments, manual gates. Done when every CI workflow is summarised.
2. **Deployable units and topology.** For each unit: where it runs (container platform, serverless, virtual machine), replicas and autoscaling, resources, exposed ports and ingress, scheduled jobs. Done when every unit is traced from source to runtime, or recorded as unknown.
3. **Environments and configuration.** Which environments exist, and how configuration and secrets reach the process (variable and secret-store names only).
4. **Observability.** Logging (structured? correlation IDs?), metrics, tracing, dashboards and alerts as code, SLOs. Judge coverage per unit against the golden signals.
5. **Resilience and failure modes.** Health and readiness probes, timeouts, retries, graceful shutdown, backups, disaster recovery. The likely failure modes of each unit and what would detect them.
6. **Operational gaps.** What an on-call engineer would lack.

## Kinds

`pipeline`, `artifact`, `deploy-unit`, `environment`, `config`, `secret-ref`, `observability`, `resilience`, `failure-mode`, `ops-gap`, `note`

## Narrative outline

Build and deploy path · Runtime topology (table: unit, platform, scaling, exposure) · Environments and configuration · Observability coverage · Resilience and failure modes · Open questions
