---
title: Designing the Data Lab Architecture
up_next: true
---

# Designing the Data Lab Architecture

> This is part of an ongoing series: **Building a Personal Data Lab**.

Coming next.

# Designing the Data Lab Architecture

In the last post, I wrote about *why* I started building a personal data lab—to create a space where I could move faster, experiment freely, and better understand how modern data and AI systems behave in practice.

This post is about what came next:

> **How I designed the architecture—and how those decisions were shaped by real constraints.**

---

## Designing Under Constraint

This is not a cloud system.

There’s no autoscaling, no managed services, no separation of concerns across clusters. Everything runs on a single machine:

- 16 cores / 32 threads  
- 256 GB RAM  
- 1 GPU (Nvidia Titan, 24 GB VRAM)  
- A mix of SSD, NVMe, and HDD storage  

That constraint changes the problem.

Instead of asking:
> “What is the best architecture?”

The question becomes:
> **“What is the best architecture when everything shares the same CPU, memory, disk, and GPU?”**

This led me to design around:
- contention  
- shared resources  
- operating modes  

---

## Walking the Architecture

Rather than thinking of the system as a set of tools, I think of it as a **flow of data with clear control and serving boundaries**.

### From Sources to Processing

Data enters the system from external sources and is handed off to Airflow.

Airflow doesn’t process the data itself—it orchestrates the work.

> **Spark is the primary processing engine**

Spark handles:
- ingestion  
- transformation  
- refinement  

and writes the results into structured tables.

---

### The Lakehouse Core: Managed Tables

Instead of writing data directly to storage in an ad hoc way, everything lands in:

> **Managed tables backed by MinIO and governed by Unity Catalog**

This creates a clean separation of concerns:

- Storage → MinIO  
- Governance → Unity Catalog  
- Compute → Spark  

This was one of the most important decisions in the design. It allows multiple systems to operate on the same data without duplication or tight coupling.

---

### Serving Paths: SQL and Graph

Once data is structured, it branches into two serving patterns.

**SQL Serving (StarRocks)**  
For analytical queries and structured exploration:
- StarRocks reads from managed tables  
- exposes fast SQL access  

**Graph Projection (Neo4j via Spark)**  
For relationship-driven use cases:
- Spark projects data into a graph model  
- Neo4j serves graph queries  

This split is intentional:

> No single system is forced to do everything.

---

### The AI Layer

On top of the serving layer sits the AI model.

It consumes data from:
- Neo4j (for graph-aware retrieval)  
- StarRocks (for structured queries)  

This is where RAG and GraphRAG workflows live.

One important constraint:

> **The GPU is a single-tenant resource.**

When the model is running, it becomes the dominant workload on the system.

---

### Access Patterns

Dashboards, notebooks, and model interactions all go through service interfaces.

In practice, as a single-user lab, I’m often connecting directly as an admin. But architecturally, I treat this as:

> **Clients interacting with platform services—not raw infrastructure.**

---

## Storage Strategy: Performance vs Reliability

Storage turned out to be one of the more interesting design problems.

I broke it into three tiers.

---

### Performance Tier (`/data/fast` – NVMe)

This is the working layer:

- Spark shuffle and temp data  
- Neo4j  
- StarRocks  
- scratch space  

This is where performance matters most.

One key lesson:

> **Leave space unused.**

I intentionally keep ~400–600 GB free to absorb:
- Spark shuffle spikes  
- temporary workloads  

---

### Reliable Tier (`/data/reliable` – RAIDZ1)

This is where the core dataset lives.

After thinking through failure modes, I added another 2TB drive and moved to:

> **RAIDZ1 (~4TB usable)**

This tier holds:
- bronze  
- silver  
- gold  

All three layers of the lakehouse live here by default.

The reasoning is practical:
- I want a consistent working dataset  
- I want to be able to reprocess data without re-ingesting  
- I want protection from a single drive failure  

Over time:

> **Bronze data is periodically offloaded to cold storage**

---

### Cold Tier (`/data/cold`)

This is the archive layer:

- older bronze data  
- raw ingestion history  
- data not part of the active working set  

The lifecycle becomes:

1. Data lands in bronze (reliable tier)  
2. Transforms produce silver and gold  
3. Older bronze data is moved to cold storage  

This keeps the reliable tier focused on *active* data.

---

## Designing Around Modes

One of the most important shifts in this design was moving away from static sizing and toward **operating modes**.

---

### Processing Mode (Batch / ELT)

- Spark dominates  
- AI model is off  
- serving is minimal  

This is where pipelines are built and data is refined.

---

### GraphRAG / AI Mode (Interactive)

- AI model is active  
- Neo4j and/or StarRocks are active  
- Spark is off  

This is where exploration and retrieval workflows happen.

---

### Hybrid Mode (Constrained)

- AI model is on  
- serving is active  
- Spark is limited  

The rule here is simple:

> Just because everything can run doesn’t mean it should.

---

## Resource Allocation as a Design Constraint

Because everything shares the same hardware, resource allocation is part of the architecture.

A rough breakdown:

- Always-on services (MinIO, Airflow, light serving): ~4 CPU / ~32 GB RAM  
- Spark (batch mode): up to ~10–12 CPU / ~80–120 GB RAM  
- AI model (8B class): GPU (12–24 GB VRAM), ~2–4 CPU, ~16–32 GB RAM  

The key principle:

> **Only one heavy workload should dominate the system at a time.**

---

## One Practical Decision: Jupyter Stays Local

I chose to run Jupyter on my laptop and connect to the platform remotely.

This keeps:
- cluster overhead low  
- resource usage predictable  
- iteration fast  

---

## What This Architecture Is (and Isn’t)

This is not:
- a production system  
- highly available  
- horizontally scalable  

This is:

> **A single-node, resource-constrained platform designed to explore modern data and AI patterns**

---

## What I’m Still Figuring Out

The system isn’t running yet.

I’m still waiting on a few hardware components (most notably the CPU cooler), and there’s a non-trivial amount of setup ahead to get everything stable.

That’s intentional.

I wanted to spend time up front thinking through:
- how resources should be allocated  
- how data should move  
- what tradeoffs I’m willing to make  

before writing pipeline code.

There are still open questions:

- how well Spark and AI workloads will coexist in practice  
- whether Neo4j and StarRocks both justify their footprint  
- how aggressively I’ll need to move bronze data to cold storage  

---

## What’s Next

The next step is turning this design into a working system—and seeing where it breaks.
