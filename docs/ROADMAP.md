# Implementation Roadmap Status

Tracking progress against the vision in `docs/VISION.md`.

## M1 — Registry foundation

| Item | Status |
|------|--------|
| Model manifest specification | Done (`docs/MANIFEST.md`) |
| JSON Schema | Done (`schemas/model-manifest.schema.json`) |
| Local registry layout | Done (`registry/`) |
| CLI: list, inspect, register, status | Done |
| Example manifest | Done (`examples/`) |

## M2 — Distribution and verification

| Item | Status |
|------|--------|
| Download (`pull`) with resume-friendly tools | Done (curl/wget) |
| SHA-256 verification | Done |
| Content-addressed artifact storage | Done |
| Quarantine on hash failure | Done |
| Audit log | Done |
| Signature verification (minisign/gpg) | Not yet |
| Resumable multi-connection downloads | Basic only |

## M3 — Local model preparation

| Item | Status |
|------|--------|
| GGUF / ONNX inspection | Scaffold |
| Hardware compatibility checks | Partial (status command) |
| Quantization adapters | Scaffold (`prepare`) |
| Derived-artifact provenance records | Spec only |

## M4 — Local deployment

| Item | Status |
|------|--------|
| llama.cpp integration | Scaffold (`deploy`) |
| Runtime lifecycle / health | Scaffold |
| Loopback-only default | Documented intent |
| Rollback | Scaffold |

## M5 — Multi-backend support

| Item | Status |
|------|--------|
| ONNX Runtime adapter | Not started |
| Backend capability detection | Not started |
| Stable adapter contract | Spec only |

## M6 — StackAlign integration

| Item | Status |
|------|--------|
| Service contract definition | Documented in VISION.md |
| Companion integration code | Not started |
| Optional discovery | Not started |

## Explicit non-goals (still hold)

- No automatic model download during StackAlign install
- No silent quantization or replacement
- No public inference binding by default
- No claim of safety/bias/license fitness merely from validation pass