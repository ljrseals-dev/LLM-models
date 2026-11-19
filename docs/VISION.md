# LLM-models Vision

This document captures the product and architectural direction for turning the repository into a local-first model registry and distribution engine.

It is derived from the strategic recommendation used to guide the update of this repository.

---

## Core Recommendation

Make `LLM-models` the **model registry and distribution engine**.

Make `StackAlign` remain the **infrastructure and LEMP layer**.

Do not turn StackAlign’s core into an AI platform. Do not turn LLM-models into another passive list of download links.

Build a **verifiable, local-first model supply chain** with a deployment interface.

### Responsibility Split

| Responsibility                         | Owner              |
|----------------------------------------|--------------------|
| Linux host provisioning                | StackAlign         |
| LEMP installation and maintenance      | StackAlign         |
| Model discovery and catalog            | LLM-models         |
| Model downloads and verification       | LLM-models         |
| Quantization and conversion            | LLM-models         |
| Inference runtime management           | LLM-models         |
| Optional service integration           | Separate adapter   |
| Host security and firewall policy      | StackAlign         |

---

## What LLM-models Should Become

### Local-first model registry and distribution engine

| Capability     | Purpose                                                                 |
|----------------|-------------------------------------------------------------------------|
| **Registry**   | Model catalog, metadata, versions, licenses, compatibility              |
| **Distribution** | Download, cache, resume, and verify model artifacts                   |
| **Validation** | Hashes, manifests, format checks, provenance, resource requirements     |
| **Conversion** | Quantization and format conversion with reproducible records            |
| **Runtime**    | Launch and manage supported local inference backends                    |
| **Operations** | Health checks, rollback, version pinning, audit history                 |

### Target User Experience

```bash
llm-models search "coding"
llm-models inspect model-name
llm-models pull model-name --version 1.2
llm-models verify model-name
llm-models prepare model-name --quantization Q4_K_M
llm-models deploy model-name
llm-models status
llm-models rollback
```

These are proposed commands, not claims of current implementation.

---

## Architecture

```
Model catalog and registry
  Metadata · versions · licenses · compatibility · provenance
        │
Artifact manager
  Download · cache · resume · SHA-256
        │
Trust and validation
  Signatures · provenance · format checks · quarantine
        │
Model preparation pipeline
  Conversion · quantization · compatibility tests · derived artifact records
        │
┌───────────────┬──────────────────┬──────────────────┐
│  llama.cpp    │  ONNX Runtime    │  Other backends  │
│  (GGUF)       │  (ONNX)          │  (adapters)      │
└───────────────┴──────────────────┴──────────────────┘
        │
Local inference service
  Loopback by default · explicit network exposure · health & lifecycle
```

---

## Distinctive Features (Priority Order)

### A. Model Manifest (not just a download URL)

Every model must have a machine-readable manifest containing at least:

- Model name, publisher, revision, and immutable version
- Original source and upstream repository
- License and usage restrictions
- Artifact format and architecture
- SHA-256 digest and signature information (where available)
- Hardware requirements and supported inference backends
- Quantization variants and their parent artifact
- Validation results and known limitations

A model is never considered verified solely because a download succeeded.

### B. Artifact Trust Chain

Model files are executable inputs to complex inference systems and can contain malicious or unsafe content.

Requirements:

- Immutable artifact identifiers
- Hash verification after download and before use
- Signature verification when a trusted signature exists
- Explicit provenance and license records
- Safe handling of archives and model serialization formats
- No automatic execution of downloaded scripts or arbitrary model-provided code
- Quarantine state for artifacts that fail validation

### C. Quantization as a Reproducible Operation

Quantization must not overwrite the original model.

```
Original model
    │
    ├── Original artifact (preserved)
    ├── Q8_0
    ├── Q5_K_M
    ├── Q4_K_M
    └── Q3_K_M
```

Every derived artifact records:

- Source hash
- Conversion tool and version
- Parameters used
- Output hash
- Validation results

### D. Backend Independence

Do not bind the registry to a single inference engine.

Initial targets:

- llama.cpp for GGUF and local CPU/GPU inference
- ONNX Runtime for ONNX-compatible models
- Additional backends through a stable adapter interface

Each backend declares its capabilities, supported formats, hardware requirements, and limitations.

### E. Deployment Safety

Deployment is explicit and reversible:

```
DISCOVERED
    ↓
DOWNLOADED
    ↓
VERIFIED
    ↓
PREPARED
    ↓
VALIDATED
    ↓
DEPLOYED
    ↓
HEALTH_CHECKED
```

Failed validation stops deployment. Failed health checks must not silently replace a previously working model.

### F. Honest Host Awareness

The system should inspect the host (memory, CPU, GPU/accelerators, storage, supported formats) and recommend suitable models and configurations with explicit trade-off explanations. It must never silently choose an oversized model or expose an inference endpoint publicly by default.

---

## Implementation Roadmap

| Milestone | Focus                                      | Outcome                                      |
|-----------|--------------------------------------------|----------------------------------------------|
| **M1**    | Registry foundation                        | Manifest spec, catalog, versioning, CLI skeleton, local registry |
| **M2**    | Distribution and verification              | Download manager, resumable transfers, content-addressed storage, checksums, quarantine |
| **M3**    | Local model preparation                    | GGUF/ONNX inspection, hardware checks, quantization adapters, derived-artifact tracking |
| **M4**    | Local deployment                           | llama.cpp integration, runtime lifecycle, local API, health checks, rollback |
| **M5**    | Multi-backend support                      | ONNX Runtime, capability detection, stable adapter contract |
| **M6**    | StackAlign integration                     | Narrow companion integration, optional service discovery |

### Strongest First Deliverable

The **manifest specification** and **artifact verification system** are the highest-leverage starting point. If those are solid, downloads, quantization, deployment, and future integrations can all build on a consistent foundation.

---

## Explicit Non-Goals

- Do not make model downloads happen automatically during ordinary StackAlign installation.
- Do not trust a model merely because it comes from a popular hosting service.
- Do not bundle model weights into the application repository.
- Do not silently quantize or replace a model.
- Do not expose an inference API on a public interface by default.
- Do not claim that a model is safe, unbiased, licensed for every use, or suitable for production simply because its validation checks passed.

---

## Long-term Vision

### A self-hosted AI infrastructure ecosystem

```
LLM-models          →  Model supply chain (discover, acquire, verify, prepare, deploy)
StackAlign          →  Linux infrastructure (provision, secure, configure, maintain)
Integration layer   →  Documented, optional interfaces between the two
```

Result: local AI infrastructure with explicit control over artifacts, deployment, and operations — no mandatory cloud model provider and no dependence on a proprietary model marketplace.

---

## Repository Status Note

The original safety and legal README work remains the public face of the repository and is preserved. The registry architecture is being built on a separate conceptual track (new feature branch / updated structure) and does not claim that the current code already implements the full platform.