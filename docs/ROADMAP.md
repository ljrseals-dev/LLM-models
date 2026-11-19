# Implementation Roadmap Status

Tracking progress against the vision in docs/VISION.md. Status reflects code in the repository, not planned behavior.

## M1 — Registry foundation

| Item | Status |
|------|--------|
| Model manifest specification | Draft (docs/MANIFEST.md) |
| JSON Schema | Present (schemas/model-manifest.schema.json) |
| Local registry layout | Implemented |
| CLI: list, inspect, register, status | Implemented |
| Schema validation at registration | Implemented; requires jq and check-jsonschema |
| Duplicate model / artifact identity rejection | Implemented |
| Example manifest | Present (examples/) |
| Multiple immutable versions per model ID | Not yet supported; one manifest per ID |

## M2 — Distribution and verification

| Item | Status |
|------|--------|
| HTTPS download (pull) | Implemented (curl or wget) |
| Resumable partial downloads | Implemented for a stable URL |
| Optional expected SHA-256 during download | Implemented |
| Content-addressed artifact storage | Implemented; no-clobber publication |
| SHA-256 verification against manifest | Implemented; fails closed |
| Quarantine on hash mismatch | Implemented |
| Audit log | Basic append-only local log |
| Signature verification (minisign/gpg) | Not implemented |
| Multi-connection downloads | Not implemented |
| Trusted signing-key policy | Not implemented |

A download without --sha256 is stored by its computed digest but remains **unverified** until a manifest declares the expected digest and verify succeeds. A checksum proves byte identity against the supplied digest; it does not establish publisher authenticity or model safety.

## M3 — Local model preparation

| Item | Status |
|------|--------|
| GGUF / ONNX inspection | Not implemented |
| Hardware compatibility checks | Partial (basic host summary only) |
| Quantization adapters | Not implemented |
| Derived-artifact provenance records | Specification only |

The prepare command exits nonzero and makes no changes until M3 is implemented.

## M4 — Local deployment

| Item | Status |
|------|--------|
| llama.cpp integration | Not implemented |
| Runtime lifecycle / health | Not implemented |
| Loopback-only default | Documented design requirement |
| Rollback | Not implemented |

The deploy and rollback commands exit nonzero and do not start or change services.

## M5 — Multi-backend support

| Item | Status |
|------|--------|
| ONNX Runtime adapter | Not started |
| Backend capability detection | Not started |
| Stable adapter contract | Specification only |

## M6 — StackAlign integration

| Item | Status |
|------|--------|
| Service contract definition | Documented in docs/INTEGRATION.md |
| Companion integration code | Not started |
| Optional discovery | Not started |

## Validation and CI

- scripts/smoke-test.sh runs isolated regression tests in a temporary registry.
- .github/workflows/ci.yml runs Bash syntax checks, ShellCheck, and the regression suite.
- Test/runtime prerequisites: Bash, jq, check-jsonschema, curl or wget, and sha256sum or shasum.

## Explicit non-goals (still hold)

- No automatic model download during StackAlign install.
- No silent quantization or replacement.
- No public inference binding by default.
- No claim of safety, bias, license fitness, publisher authenticity, or production suitability merely from a checksum pass.
