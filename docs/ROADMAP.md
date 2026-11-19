# Implementation Roadmap Status

Tracking progress against docs/VISION.md. Status reflects code in the repository, not planned behavior.

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

A download without --sha256 is stored by its computed digest but remains unverified until a manifest declares the expected digest and verification succeeds. A checksum proves byte identity against the supplied digest; it does not establish publisher authenticity or model safety.

## M3 — Local model quantization and preparation

| Item | Status |
|------|--------|
| ONNX artifact selection from manifest | Implemented; requires exactly one match or --artifact |
| FP16 weight conversion | Implemented; preserves model I/O tensor types |
| Dynamic INT8 weight quantization | Implemented through ONNX Runtime; per-channel, selected operator types |
| Packed 2-bit ternary weights | Implemented; NPZ sidecar and per-output-channel scales |
| Ternary executable ONNX model | Implemented by reconstructing FLOAT weights; not native ternary arithmetic |
| Quantization provenance | Implemented; source/output hashes, tool versions, parameters, derived-manifest fragment |
| Verify source artifact before preparation | Implemented; digest rechecked immediately before conversion |
| FLOAT16 initializer fallback | Implemented; promotes to FLOAT32 |
| Signed INT8 DequantizeLinear fallback | Implemented; initializer-backed scalar/per-axis parameters only |
| Packed ternary fallback | Implemented; requires explicit cmajor.ternary metadata contract |
| ONNX operator allowlist | Implemented; unsupported operators fail closed |
| Cmajor patch generation | Implemented; templates bundled with upstream notices |
| Derived-artifact provenance | Implemented; source and generated-file SHA-256 recorded |
| External ONNX tensor-data references | Refused; self-contained ONNX artifact required |
| GGUF quantization (Q4/Q5/Q8 etc.) | Not implemented |
| Compression-preserving quantized Cmajor runtime | Not implemented; current fallbacks expand weights to FLOAT32 |
| Hardware compatibility / memory estimate | Not implemented beyond basic host summary |
| Cmajor compilation | Not yet verified in CI |
| ONNX Runtime vs Cmajor numerical parity | Not implemented |

The quantize command produces FP16, dynamic INT8, or packed ternary artifacts under registry/quantized/ (or an explicit new output path). It does not mutate the source manifest; derived-manifest.fragment.json records output artifacts and parentage for a separately versioned manifest.

The prepare command converts a verified ONNX artifact into a Cmajor patch under registry/prepared/ (or an explicit new output path). The supported fallback transformations are those already developed in ljrseals-dev/schema. They are conversion fallbacks: generated Cmajor constants are FLOAT32, not packed INT8 or ternary weights. Realm-Quant's packed ternary sidecar is not yet consumed by the Cmajor emitter, and dynamic INT8 may introduce ONNX operators outside the Cmajor allowlist. See tools/onnx/README.md for contracts, refusal cases, dependencies, and licensing.

## M4 — Local deployment

| Item | Status |
|------|--------|
| llama.cpp integration | Not implemented |
| ONNX Runtime adapter | Not implemented |
| Runtime lifecycle / health | Not implemented |
| Loopback-only default | Documented design requirement |
| Rollback | Not implemented |

The deploy and rollback commands exit nonzero and do not start or change services.

## M5 — Multi-backend support

| Item | Status |
|------|--------|
| Backend capability detection | Not started |
| Stable adapter contract | Specification only |
| Runtime interoperability tests | Not started |

## M6 — StackAlign integration

| Item | Status |
|------|--------|
| Service contract definition | Documented in docs/INTEGRATION.md |
| Companion integration code | Not started |
| Optional discovery | Not started |

## Validation and CI

- scripts/smoke-test.sh runs isolated registry regression tests in a temporary registry.
- tools/onnx/test_fallback.py tests numeric FLOAT16, INT8, and ternary fallback transforms.
- tools/onnx/test_prepare.py tests verified ONNX-to-Cmajor generation, provenance hashes, and no-overwrite behavior.
- tools/onnx/test_cli_prepare.sh tests the public registry pull-to-prepare lifecycle with a synthetic ONNX fixture and fake downloader.
- tools/quantization/test_quantization.py and test_onnx_integration.py test packing, FP16, dynamic INT8, ternary output, ONNX Runtime execution, and numerical comparison.
- tools/quantization/test_cli_quantize.sh tests registry pull-to-quantize and derived sidecar/provenance output.
- .github/workflows/ci.yml runs Bash syntax checks, ShellCheck, Python ONNX tests, and shell regression tests.
- Test/runtime prerequisites: Bash, jq, check-jsonschema, Python 3.11+, NumPy, ONNX, ONNX Runtime, onnxconverter-common (FP16), pytest, curl or wget, and sha256sum or shasum.

## Explicit non-goals (still hold)

- No automatic model download during StackAlign install.
- No silent quantization or replacement.
- No public inference binding by default.
- No claim of safety, bias, license fitness, publisher authenticity, or production suitability merely from a checksum pass.
