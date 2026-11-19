# Model Configuration Feasibility and Benchmark Eligibility Lifecycle

**Status:** Governance and research contract; documentation only.  
**Baseline:** `main` at `ab5a7bb1b0598f7407c0d6a3b671e819ba52be5d`.  
**Purpose:** Define the authoritative model/artifact lifecycle gates and evidence requirements for deciding which local inference configurations are feasible and which workloads have actually passed measurement.

This document belongs in LLM-models because this repository owns the model supply chain: discovery, manifests, artifact acquisition, integrity/provenance, quarantine, preparation, and the planned runtime lifecycle. It does not claim that the current implementation already provides a benchmark runner, GPU execution provider, or measured model leaderboard.

## 1. Governing principles

- Treat a configuration as a model revision plus exact artifact set and inference settings, not merely a model name.
- License, runtime/format compatibility, and privacy/network requirements are independent hard gates.
- Never infer host hardware. Missing required host facts produce `HOST_UNRESOLVED`.
- Pre-download storage and memory calculations are estimates, not proof of fit.
- Fetch failures are distinct from integrity failures.
- A hash mismatch is quarantined. Absence of a publisher-provided expected hash is `INTEGRITY_UNVERIFIABLE`, not mismatch.
- After successful artifact verification, recalculate memory feasibility using actual downloaded size and verified format metadata.
- Pin threshold profiles, workload specifications, and test-set revisions before execution.
- Evaluate coding, reasoning, chat, and document ingestion independently.
- `ELIGIBLE` requires actual local execution, complete metrics, and passing pre-registered thresholds.
- Hosted API results must never be labeled `LOCAL_MEASURED`.
- Unknown or unmeasured values remain null; null is not zero, pass, or fail.

## 2. Configuration, artifact, host, and run identity

A configuration is the complete inference configuration:

`(model revision, artifact set, quantization, context, batch/sequences, KV precision, runtime/version, backend, placement, flags)`

Keep identity scopes separate:

- `model_id`: registry identity for the model.
- `artifact_id`: exact immutable artifact identity, including format, byte size, and digest.
- `config_id`: stable identifier derived from canonicalized model/artifact identity and inference settings.
- `host_record_id`: immutable hardware/software environment snapshot.
- `run_id`: unique execution of one configuration on one host for one workload and test-set revision.

Canonical serialization for hash-derived identifiers must specify schema version, field ordering, number representation, null handling, and string normalization.

A host record should include OS/release/kernel/architecture, CPU, total and available RAM, accelerator model, total and available VRAM or unified memory, memory topology, storage capacity/free space, driver/runtime versions, power mode, and relevant thermal conditions. Record collection method and timestamp. Unknown values remain null; do not infer a hardware tier.

## 3. Feasibility mathematics

These calculations are pruning estimates. Actual backend allocations, process memory, sustained execution, and thermal behavior require measurement.

### 3.1 Weight storage

A rough estimate is:

`W_est = P × (b / 8) × (1 + m)`

where `P` is parameter count, `b` is assumed effective bits per weight, and `m` is an explicit overhead allowance for quantization metadata, scales, tensor alignment, padding, and format-specific storage.

Named formats such as `Q4_K_M` are mixed/block quantization formats. Do not assume exactly four bits for every parameter.

Evidence precedence:

1. Actual downloaded artifact byte size.
2. Publisher/host file metadata, labeled `VENDOR_CLAIM` until verified locally.
3. Tensor- and format-aware estimate, labeled `ESTIMATED`.
4. Parameter-count × nominal-bits estimate, labeled `ESTIMATED` with assumptions.

For split/sharded models, record every required file, its size, and its hash. Actual artifact size takes precedence over the rough parameter estimate.

### 3.2 KV cache

For a conventional uniform transformer:

`KV_est = 2 × B × T × L × H_kv × D_head × kv_bytes`

where `B` is resident sequence count, `T` is allocated context per sequence, `L` is the number of cache-contributing layers, `H_kv` is the number of key/value heads (not query heads), `D_head` is head dimension, and `kv_bytes` is bytes per cached element.

Use architecture-aware per-layer accounting for grouped-query/multi-query attention, sliding windows, hybrid or recurrent layers, shared caches, quantized cache, differing K/V precision, and other non-uniform architectures. Record batch/sequence count and context. Advertised maximum context is not evidence that a particular host can allocate it.

### 3.3 Compute buffers and reserve

A coarse placeholder may be:

`C_est = max(backend_floor, context_tokens × compute_coefficient)`

Both terms must be backend-, architecture-, batch-, and configuration-specific. Use this only for early pruning; record estimator version and assumptions.

Let:

`R = os_reserve + display_reserve + backend_context_reserve + other_required_reserve`

Then:

`B_usable = B_assigned - R`

Resident estimate passes only when:

`W + KV + C ≤ B_usable`

Do not count reserve twice.

### 3.4 Host topology

- **Unified memory:** CPU and accelerator allocations consume one shared physical pool. Do not add nominal GPU memory to RAM as independent budgets.
- **Discrete GPU + system RAM:** maintain separate RAM and VRAM budgets; account for actual weight/KV/buffer placement and partial-offload staging/transfer memory.
- **CPU-only:** use the available system-RAM budget and record mapped/resident behavior and storage constraints.
- **Unknown topology:** set topology unresolved and transition to `HOST_UNRESOLVED`; do not substitute a representative hardware tier.

### 3.5 Storage and mapped candidates

Before download, ensure free storage covers all shards, temporary/partial files, conversion output, and retained source artifacts, plus an explicit storage reserve.

Memory mapping is not free memory. Pages can fault into RAM during inference, and page faults, paging, storage throughput, and cache churn can make a theoretically loadable model unusable. `MAPPED_ESTIMATE` is a candidate classification only; it becomes measured fit only after successful execution and sustained-load measurements.

## 4. Normative configuration lifecycle

```text
CONFIGURATION CREATED
   |
   +-- LICENSE           --> LICENSE_PRUNED
   +-- COMPATIBILITY     --> COMPATIBILITY_PRUNED
   +-- PRIVACY/NETWORK   --> PRIVACY_PRUNED
   |
HOST IDENTIFICATION
   +-- unknown           --> HOST_UNRESOLVED
   |
STORAGE + MEMORY (estimate)
   +-- impossible        --> MEMORY_PRUNED
   +-- estimate ok       --> RESIDENT_ESTIMATE | MAPPED_ESTIMATE
   |
DOWNLOAD
   +-- fetch failed      --> FETCH_FAILED
   |
HASH / PROVENANCE
   +-- mismatch          --> INTEGRITY_QUARANTINED
   +-- no published hash --> INTEGRITY_UNVERIFIABLE
   +-- verified          --> re-run memory math with measured size
                              +-- still fits --> READY_FOR_BENCHMARK
                              +-- now exceeds --> MEMORY_PRUNED
   |
THRESHOLD PROFILE PRESENT
   +-- absent            --> UNRESOLVED
   |
FAN OUT: coding | reasoning | chat | doc-ingest
   per workload:
     LOAD_FAILED | HARNESS_FAILED | ACCURACY_FAILED
     | PERFORMANCE_FAILED | SUSTAINED_LOAD_FAILED
     | ELIGIBLE (requires LOCAL_MEASURED + thresholds + metrics)
```

### 4.1 Gate semantics

- **License, compatibility, privacy/network:** independent hard gates. Pruning applies to the affected configuration and intended use, not automatically every deployment or quantization of a model.
- **Host identification:** missing required host/topology inputs produce `HOST_UNRESOLVED`. Never infer hardware.
- **Pre-download storage/memory:** estimator outputs only. Record inputs, assumptions, estimator version, and evidence class. `RESIDENT_ESTIMATE` and `MAPPED_ESTIMATE` are not measured fit.
- **Fetch failure:** timeouts, unavailable sources, network errors, and interrupted transfers produce `FETCH_FAILED`; they are distinct from integrity failures.
- **Hash/provenance mismatch:** produce `INTEGRITY_QUARANTINED`. Do not load, prepare, deploy, or benchmark the artifact. Preserve expected source/hash, observed hash, artifact identity, and reason.
- **No published expected hash:** produce `INTEGRITY_UNVERIFIABLE`, not mismatch. A locally computed hash identifies downloaded bytes for repeatability but does not prove publisher provenance. Any lower-trust research exception must be an explicit policy decision and remain visibly marked.
- **Successful integrity verification:** rerun memory feasibility with actual artifact size and verified format metadata. If actual size exceeds budget, transition to `MEMORY_PRUNED`.
- **Threshold profile:** pin profile ID/revision, workload spec, and test-set revision before execution. Missing profile means `UNRESOLVED`; never invent default thresholds.
- **Workload fan-out:** create independent results for coding, reasoning, chat, and document ingestion. A failure in one does not overwrite another.

### 4.2 Configuration and workload states

Configuration-level states:

- `LICENSE_PRUNED`
- `COMPATIBILITY_PRUNED`
- `PRIVACY_PRUNED`
- `HOST_UNRESOLVED`
- `MEMORY_PRUNED`
- `RESIDENT_ESTIMATE`
- `MAPPED_ESTIMATE`
- `FETCH_FAILED`
- `INTEGRITY_QUARANTINED`
- `INTEGRITY_UNVERIFIABLE`
- `READY_FOR_BENCHMARK`
- `UNRESOLVED`

Per-workload states:

- `PENDING`
- `LOAD_FAILED`
- `HARNESS_FAILED`
- `ACCURACY_FAILED`
- `PERFORMANCE_FAILED`
- `SUSTAINED_LOAD_FAILED`
- `ELIGIBLE`

Do not collapse workload outcomes into one configuration pass/fail field. Preserve gate history and independent workload-result records.

## 5. Workload eligibility contract

`ELIGIBLE` is a per-workload result and requires all of the following:

1. Exact artifact/configuration passed the applicable integrity policy.
2. The run executed locally on the identified host with recorded runtime, version, backend, placement, and flags.
3. The workload harness completed successfully; otherwise report `HARNESS_FAILED`.
4. Pinned workload and test-set revisions were used.
5. Accuracy, latency, throughput, memory, and sustained-load thresholds applicable to that workload were met.
6. Required metrics are present and valid; null cannot satisfy a threshold.
7. Evidence is classified `LOCAL_MEASURED` and linked to raw logs or a content-addressed evidence record.

Hosted API runs must use a distinct evidence/result path and cannot satisfy `LOCAL_MEASURED`. They may support separately labeled online comparisons, but never a local eligibility claim.

## 6. Workload separation and metrics

- **Coding:** fixed repository tasks, patch correctness, test outcomes, and reproducible grading.
- **Reasoning:** fixed problems with objective answer checks and rubric-scored explanations where needed.
- **Chat:** fixed prompt suite, instruction adherence, and documented human/rubric evaluation.
- **Document ingestion:** separate PDF extraction/OCR, chunking, retrieval, source attribution, citation fidelity, and long-document coverage tests. Document-ingestion consumers such as LLM-zip-pdf should contribute workload-specific harnesses and results; they should not redefine the registry's shared artifact lifecycle.

A run record should preserve at least:

- configuration, model, artifact, host, run, workload, workload-spec, test-set, and threshold-profile identifiers/revisions;
- load success and placement;
- prompt/output token counts, sequence count, concurrency, warm-up policy, repetitions, and measurement method;
- TTFT, throughput, peak RSS, peak VRAM, sustained-load duration, thermal-throttle observation, and energy where relevant;
- failure reason, evidence class, timestamp, and raw-log hash/reference.

Unknown or unmeasured fields remain null, never zero.

## 7. Evidence classes

| Class | Meaning | Example |
|---|---|---|
| `UNVERIFIED` | No supporting check recorded | Unknown publisher hash |
| `VENDOR_CLAIM` | Publisher/provider statement | Published model size or API price |
| `ESTIMATED` | Reproducible calculation from declared inputs | Predicted KV-cache size |
| `VERIFIED` | Integrity check completed against an expected value | Downloaded artifact matches expected SHA-256 |
| `LOCAL_MEASURED` | Actual local execution with host, workload, method, and metrics recorded | Peak RSS and tokens/sec on identified host |

A verified hash proves identity relative to the expected hash; it does not establish model quality, safety, or license rights. Vendor claims and estimates cannot independently produce `ELIGIBLE`.

## 8. Repository ownership and integration boundaries

LLM-models owns:

- model and artifact manifests, immutable identities, and revision/provenance metadata;
- discovery and explicit acquisition;
- download resumption, digest verification, and quarantine;
- derived-artifact lineage for quantization/conversion;
- feasibility records and configuration eligibility evidence;
- future runtime adapters, deployment lifecycle, health checks, and rollback, subject to separate implementation and review.

Consumer boundaries:

- **StackAlign** owns host infrastructure and security. Its integration with LLM-models should remain optional and narrow; it must not become the model registry or silently download models during ordinary host provisioning.
- **LLM-zip-pdf** owns PDF/ZIP document processing and its document-ingestion harness. It consumes explicitly selected local models and reports workload outcomes; it does not own shared model acquisition or provenance policy.

This document is a policy/acceptance contract, not a new runtime feature. It adds no benchmark runner, remote execution provider, automatic updater, telemetry, public inference exposure, or model download behavior.

## 9. Acceptance checklist for future implementation

- [ ] Versioned canonical configuration identity; separate model, artifact, host, and run identities.
- [ ] Unknown hardware remains unresolved.
- [ ] Architecture-aware KV estimator with explicit assumptions.
- [ ] Separate unified-memory, discrete-GPU, and CPU-only budget paths.
- [ ] Storage reserve and actual artifact-size recheck.
- [ ] Mapped execution remains a candidate until measured.
- [ ] License, compatibility, privacy/network gates are independent.
- [ ] Fetch errors are distinct from integrity failures.
- [ ] Missing publisher hash is `INTEGRITY_UNVERIFIABLE`.
- [ ] Hash mismatch is quarantined and cannot be loaded, prepared, deployed, or benchmarked.
- [ ] Threshold profiles and test-set revisions are pinned before execution.
- [ ] Coding, reasoning, chat, and doc-ingest outcomes are independent.
- [ ] Null metrics cannot satisfy thresholds.
- [ ] No result is `LOCAL_MEASURED` without actual local execution and complete evidence.
- [ ] Hosted results cannot satisfy local eligibility.
- [ ] Consumer integrations remain optional and respect repository ownership boundaries.
- [ ] No model downloads, host changes, or benchmark claims are made by documentation alone.

**Conclusion:** LLM-models should discover and acquire candidates, estimate feasibility, verify exact artifacts, and preserve provenance. A future benchmark runner may then establish what works on a specific host and workload through reproducible local measurement. Keep estimates, vendor claims, integrity verification, and measured outcomes distinct throughout the supply chain.
