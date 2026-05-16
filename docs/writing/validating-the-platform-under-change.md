---
title: validating-the-platform-under-change
date: 2026-05-16
---

# Validating the Platform Under Change

## BLUF

The previous phases of this series focused on designing the architecture and assembling the initial infrastructure for the lab.

This phase focused on something different:

> validating whether the architecture actually behaves correctly under disruption, rebuild, and operational lifecycle conditions.

The turning point came unexpectedly through hardware failure. A motherboard replacement forced the system through its first meaningful disruption while scaling toward 256GB of RAM. Rather than simply restoring the machine, I used the rebuild to validate whether the system architecture could survive change without requiring reconstruction.

That process exposed hidden configuration drift, validated the durability boundaries between storage and compute, and ultimately led to a broader operational maturity effort across the stack.

The work evolved through three repositories with intentionally separated responsibilities:

- `infra-validate`
  - validates Linux host health, ZFS storage integrity, Kubernetes readiness, and stateful workload behavior

- `data-platform`
  - deploys and verifies MinIO and Spark on the existing K3s substrate through repeatable deployment, teardown, rebuild, and verification workflows

- `data-lab`
  - consumes the platform runtime for interactive notebooks, Spark experimentation, and workload validation without mutating infrastructure behavior

The goal throughout this phase was consistent:

> reduce operational ambiguity before increasing architectural complexity.

Each layer was only expanded after the previous layer became operationally verifiable.

This is intentionally still a constrained single-node environment. The goal is not high availability or cloud-scale throughput. The goal is developing operational understanding through explicit contracts, repeatable validation, and deterministic behavior.

---

# Hardware Failure as Architectural Validation

## BLUF

The motherboard replacement unintentionally became the first real resilience test of the architecture.

The important outcome was not that the machine came back online. The important outcome was that durable state survived independently of runtime infrastructure and compute services.

That behavior validated one of the core architectural goals established earlier in the series:

> storage should remain durable while compute and orchestration remain replaceable and recoverable.

## Identifying the Failure

The original issue surfaced while attempting to scale the system beyond 128GB of RAM.

Symptoms included:

- inconsistent DIMM behavior
- unstable memory channel population
- intermittent recognition failures

After isolating DIMMs and validating CPU behavior, the issue ultimately traced back to motherboard instability rather than memory or processor failure.

The replacement board immediately stabilized memory behavior.

From there, validation proceeded incrementally:

- 128GB
- 192GB
- progressing toward 256GB

Rather than assuming success because the machine booted, the system was validated under sustained load using:

- incremental DIMM population
- `stress-ng`
- `dmesg` inspection
- channel population verification

One important lesson became immediately clear:

> High-capacity memory systems are validated under load—not at boot.

---

# Discovering Configuration Drift

## BLUF

The most valuable problem uncovered during the hardware swap was not hardware-related.

It was operational drift that had accumulated silently over time.

During post-swap validation, running:

```bash
mount -a
```

produced:

```text
Structure needs cleaning on /mnt/data
```

At first glance this appeared to be a storage failure.

It was not.

The actual durable storage layer (`tank`) remained healthy and fully intact.

The issue was a stale XFS mount configuration tied to a previously removed 1TB drive that still existed inside `/etc/fstab`.

The architecture itself had survived correctly.

The configuration surrounding it had not.

Resolution involved:

- removing orphaned mount entries
- validating clean mount state
- confirming ZFS as the single durable source of truth

This reinforced an important operational reality:

> Hardware changes expose assumptions and configuration drift that otherwise remain hidden indefinitely.

More importantly, it validated the architectural separation established earlier in the project:

| Layer | Responsibility |
|---|---|
| ZFS (`tank`) | Durable state |
| NVMe (`/fast`) | Performance / staging |
| K3s + containers | Recoverable runtime compute |
| OS install | Replaceable orchestration substrate |

The system behaved according to design intent:

- data survived
- compute was recoverable
- runtime services were reproducible
- recovery remained deterministic

That was the real milestone of this phase.

---

# infra-validate: Proving Stateful Readiness

## BLUF

Once the hardware stabilized, the focus shifted from:

> “the system runs”

to:

> “the system is operationally ready to safely support stateful services.”

This led to the continued expansion of `infra-validate`.

`infra-validate` does not provision infrastructure or install Kubernetes.

Its purpose is validating whether the Linux, ZFS, and K3s substrate is behaving according to expected operational assumptions before platform services are deployed.

## Moving Beyond “Healthy”

A major realization during this phase was that Kubernetes status alone is not a sufficient readiness signal.

A cluster can report:

- healthy nodes
- bound PVCs
- mounted storage

…and still fail under real lifecycle conditions.

The validation layer therefore expanded into capability-based checks rather than configuration checks.

The primary readiness gate became:

```bash
python -m infra_validate run --config config/lab.yaml
```

Validation coverage now includes:

### Host / System

- hostname
- uptime
- memory thresholds
- disk free thresholds
- required systemd services

### ZFS / Storage

- pool health
- dataset existence
- required mounts
- filesystem type validation
- expected storage paths

### Kubernetes Readiness

- cluster reachability
- node readiness
- namespace validation
- workload readiness
- warning-event hygiene

### Stateful Workload Validation

The most important addition was persistence validation.

A dedicated durable storage smoke workflow validates:

- PVC provisioning
- pod mount behavior
- read/write behavior
- persistence across restart

```bash
./scripts/durable_smoke_run.sh
```

This intentionally validates real workload lifecycle behavior rather than merely checking resource existence.

The key shift in thinking was:

> readiness should be proven behaviorally—not assumed from configuration state.

---

# data-platform: Deterministic Stateful Services

## BLUF

Once the substrate became operationally verifiable, the next step was validating whether stateful platform services could be deployed, rebuilt, and verified repeatably on top of it.

This work lives inside `data-platform`.

The repository does not create the K3s substrate itself.

Instead, it assumes a validated substrate exists and focuses on deterministic service lifecycle management.

The operational progression became:

```text
deploy
→ validate
→ teardown
→ rebuild
→ verify
```

## Establishing Stateful Service Patterns with MinIO

MinIO became the first fully validated stateful platform service.

More importantly, it established the initial operational patterns later services will reuse.

The deployment flow intentionally separates:

- operators
- platform workloads

using layered Helmfile composition.

Deployment sequence:

```bash
helmfile -f releases/helmfile.yaml -l layer=operators apply
services/minio/scripts/sync-root-secret.sh
helmfile -f releases/helmfile.yaml -l layer=platform-core apply
```

This phase also introduced:

- SOPS-managed secrets
- runtime Kubernetes secret materialization
- durable storage contracts
- repeatable service verification

The durable storage boundary was formalized through:

```yaml
storageClassName: durable
```

This directly aligns MinIO persistence with the validated ZFS durability layer established earlier.

## Verification Over Assumption

A major operational principle emerged here:

> deployment success is not service acceptance.

MinIO verification explicitly validates:

- tenant readiness
- bucket existence
- object CRUD behavior
- credential export paths
- optional persistence validation

Baseline buckets are also now established and verified automatically:

- `platform-validation`
- `lake-bronze`
- `lake-silver`
- `lake-gold`

This created the first durable storage boundaries for the platform.

---

# Spark: Eliminating Runtime Ambiguity

## BLUF

With stateful object storage validated, the next step was establishing deterministic distributed compute behavior through Spark running on Kubernetes against MinIO.

The goal was not simply “getting Spark to run.”

The goal was reducing ambiguity in:

- runtime selection
- image versioning
- TLS trust
- storage boundaries
- workload verification
- rebuild behavior

## Why Spark?

Spark exists in the architecture as the bridge between:

- interactive experimentation
- distributed compute validation
- future orchestration workflows

It provides the first scalable compute layer capable of validating:

- distributed dataframe operations
- numerical workloads
- object storage integration
- future promotion workflows

## Deterministic Runtime Behavior

Several subtle issues surfaced during implementation:

- stale image reuse
- S3A configuration mismatches
- TLS trust failures
- implicit bucket assumptions
- brittle verification logic

None were catastrophic individually.

Together, they exposed a broader problem:

> distributed systems fail through ambiguity far more often than catastrophic failure.

To reduce drift, Spark workloads now rely on:

- timestamped versioned images
- deterministic image selection
- explicit truststore synchronization
- platform-owned runtime configuration

Example build flow:

```bash
services/spark/scripts/build-versioned-image.sh
```

Truststore synchronization:

```bash
services/spark/scripts/sync-minio-truststore.sh
```

## Validation Boundaries

Validation outputs are intentionally isolated from future medallion data layers.

Spark validation workloads write only to:

```text
s3a://platform-validation/spark/...
```

This separation ensures:

- validation workloads remain disposable
- medallion layers remain protected
- operational boundaries stay explicit

The platform also moved beyond smoke tests into deterministic numerical validation workloads involving:

- matrix operations
- joins
- pivots
- aggregate validation

At this point the question began shifting from:

> “Does distributed compute execute?”

to:

> “Does distributed compute produce correct and repeatable results?”

---

# data-lab: Runtime Contract Convergence

## BLUF

Once the infrastructure and platform layers became operationally repeatable, the next challenge was interactive development.

The goal was enabling notebook-driven experimentation without accidentally creating a second platform with duplicated runtime behavior.

This work lives in `data-lab`.

## Interactive Workflows Without Platform Drift

A major design decision during this phase was intentionally *not* deploying a full notebook platform like JupyterHub.

This remains a constrained single-node environment optimized for operational clarity and deterministic validation—not multi-tenant orchestration complexity.

Instead, the workflow intentionally stays lightweight:

```text
VS Code
  → Remote SSH
    → Ivaldi (Spark driver)
      → K3s executors
        → MinIO
```

The Spark driver remains colocated with the cluster to avoid:

- callback routing complexity
- VPN/firewall fragility
- TLS inconsistency
- networking ambiguity

## Shared Runtime Contracts

The most important architectural decision in this layer was eliminating runtime duplication.

`data-lab` consumes runtime truth directly from `data-platform`, including:

- Spark shared configuration
- Spark mode configuration
- MinIO tenant configuration
- MinIO NodePort configuration

This creates a single runtime contract shared between:

- interactive notebook workflows
- operator-driven Spark workloads

That convergence became one of the strongest architectural outcomes of the phase.

Interactive and operator execution now differ primarily in topology—not runtime truth.

## Notebook Validation Workflows

`data-lab` also introduced repeatable notebook validation workflows.

Fast verification:

```bash
scripts/verify-repo.sh
scripts/verify-notebook-integration.sh
scripts/verify-interactive-spark.sh
```

Full notebook acceptance validation:

```bash
scripts/test-platform-integration-notebooks.sh
```

These workflows validate:

- SparkApplication submission
- interactive Spark behavior
- MinIO integration
- notebook execution
- platform contract alignment

The notebooks themselves intentionally model the promotion path expected later in the platform lifecycle:

```text
interactive exploration
→ deterministic notebook validation
→ promoted Spark workload
→ integrated platform verification
→ future orchestration
```

The important realization here was:

> interactive tooling should accelerate validation—not become a parallel platform.

---

# Next Steps

## BLUF

At this point, the platform foundation is intentionally stable enough to stop adding infrastructure complexity and begin exercising the system through a small real-world workflow.

The next phase will focus on implementing a constrained data refinement experiment designed to expose the actual operational experience of working inside the platform before introducing additional architectural layers.

Rather than continuing to expand the stack prematurely, the goal is now to let future platform adjustments emerge from real workload pressure and operational friction.

The focus shifts from:

> “Can the platform support distributed systems concepts?”

to:

> “What actually becomes painful, ambiguous, or limiting during real usage?”

The planned workflow will intentionally remain small in scope while exercising the existing system end-to-end:

```text
raw data ingestion
→ refinement / transformation
→ validation
→ persisted outputs
→ interactive analysis
→ promoted distributed execution
```

This phase is expected to surface:

- workflow friction
- runtime assumptions
- storage boundary issues
- orchestration gaps
- metadata and lineage needs
- reproducibility concerns
- promotion workflow weaknesses

Most importantly, it will allow future architectural decisions to be driven by demonstrated need rather than theoretical completeness.

At this stage, resisting unnecessary complexity is more valuable than adding additional services.

---

# Closing Thoughts

This phase marked the transition from:

> designed architecture

to:

> operationally validated architecture.

The most important outcome was not deploying additional services.

It was reducing ambiguity across the system before increasing complexity.

Each layer now has explicit operational boundaries:

| Repository | Responsibility |
|---|---|
| `infra-validate` | substrate readiness validation |
| `data-platform` | deterministic service lifecycle |
| `data-lab` | interactive experimentation and workload validation |

The system is still intentionally constrained:

- single-node
- local-storage-backed
- operationally simple by design

The goal is not cloud-scale throughput or production HA.

The goal is understanding and validating the operational behavior of modern data platform patterns through explicit contracts, repeatable rebuilds, and deterministic workflows.

At this point, the platform is no longer merely assembled.

It is operationally verifiable.

And that changes the nature of every future layer built on top of it.

---

## Series: Building a Personal Data Lab

- Part 1: [Why I Built a Data Lab](data-lab-why.md)  
- Part 2: [Designing the Data Lab Architecture](data-lab-architecture.md)  
- Part 3: [Implementing the Data Lab](implementing-the-data-lab.md)
- Part 4: Validating the Platform Under Change *(this post)*

→ Next: [Data Lab Test Dive](data-lab-test-drive.md) *(coming next)*