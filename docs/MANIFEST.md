# Model Manifest Specification (Draft — M1)

A model in LLM-models is identified and described by a **manifest**.  
The manifest is the source of truth for identity, provenance, trust, and capability metadata.

A model is never considered verified solely because a file was downloaded.

---

## Goals

- Give every model an immutable, machine-readable identity
- Record provenance, license, and trust information explicitly
- Support both original and derived artifacts (e.g. quantizations)
- Enable automated verification and safe deployment decisions
- Remain readable by humans and processable by tools

---

## Manifest Format

- Primary format: **JSON**
- Schema: `schemas/model-manifest.schema.json`
- Encoding: UTF-8
- Recommended filename: `model.manifest.json` (or `<model-id>.manifest.json`)
- Registration validates against the JSON Schema using `check-jsonschema` and requires `jq`; validation fails closed when either tool or the schema is unavailable.

---

## Required Fields

| Field                | Type     | Description |
|----------------------|----------|-------------|
| `manifest_version`   | string   | Schema version of this manifest (e.g. `"1.0"`) |
| `id`                 | string   | Stable model identifier (recommended: reverse-domain or publisher/name) |
| `name`               | string   | Human-readable name |
| `version`            | string   | Immutable version string for this artifact set |
| `publisher`          | string   | Publisher or organization |
| `description`        | string   | Short description |
| `license`            | object   | License information |
| `source`             | object   | Upstream provenance |
| `artifacts`          | array    | One or more artifacts that belong to this model version |

### `license` object

```json
{
  "spdx": "Apache-2.0",
  "name": "Apache License 2.0",
  "url": "https://www.apache.org/licenses/LICENSE-2.0",
  "restrictions": "Optional free-text notes about usage limitations"
}
```

At least one of `spdx` or `name` is required.

### `source` object

```json
{
  "upstream_repo": "https://huggingface.co/example/model",
  "upstream_revision": "abc123...",
  "original_url": "https://...",
  "retrieved_at": "2026-11-18T00:00:00Z",
  "notes": "Optional free-text provenance notes"
}
```

### `artifacts` array

Each entry describes one concrete file (original weights, a specific quantization, etc.).

```json
{
  "id": "artifact-id",
  "role": "original | quantized | converted | other",
  "format": "gguf | onnx | safetensors | pytorch | other",
  "filename": "model-Q4_K_M.gguf",
  "size_bytes": 1234567890,
  "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "signature": {
    "type": "minisign | gpg | other",
    "value": "...",
    "public_key_id": "..."
  },
  "quantization": {
    "method": "Q4_K_M",
    "parent_artifact_id": "original-artifact-id",
    "tool": "llama.cpp",
    "tool_version": "b1234",
    "parameters": {}
  },
  "hardware_requirements": {
    "min_ram_mb": 8192,
    "recommended_ram_mb": 16384,
    "gpu": "optional | required | none",
    "notes": ""
  },
  "supported_backends": ["llama.cpp", "onnxruntime"],
  "validation": {
    "status": "unverified | verified | quarantined | failed",
    "checked_at": "2026-11-18T00:00:00Z",
    "checks": [
      {
        "name": "sha256",
        "result": "pass | fail | skipped",
        "details": ""
      }
    ]
  }
}
```

---

## Recommended Optional Fields

- `tags` — array of strings (e.g. `["coding", "instruct", "7b"]`)
- `parameters` — approximate parameter count (string or number)
- `architecture` — model architecture family
- `context_length` — maximum context if known
- `known_limitations` — free-text or structured notes
- `compatibility` — notes about tokenizer, chat template, etc.

---

## Identity and Immutability Rules

1. The combination of `id` + `version` should be unique within a registry.
2. Once an artifact’s `sha256` is recorded and marked verified, the file content must not change.
3. Derived artifacts (quantizations, conversions) must reference their parent via `quantization.parent_artifact_id` (or equivalent) and record the tool + parameters used.
4. Changing any trust-relevant field (hashes, signatures, license, source) requires a new version or a new artifact entry.

---

## Registry Implementation Boundaries

The current M1/M2 CLI stores one immutable manifest per model ID. Registering the same ID again is rejected rather than silently replacing its manifest. Multiple concurrently registered versions for one model ID are planned work and are not yet supported. Artifact IDs must be unique within a manifest. Artifact filenames are basenames only; path separators are rejected.

A SHA-256 match establishes byte identity against the digest in the manifest. It does not establish who published the artifact, whether the publisher is authentic, whether redistribution is licensed, or whether the model is safe. Signature verification and trusted-key management are not implemented.

## ONNX quantization and preparation semantics

An artifact with format "onnx" can be selected by the quantize or prepare command. Quantize supports FP16 weight conversion, ONNX Runtime dynamic INT8 weight quantization for selected operator types, and packed 2-bit ternary sidecars with per-output-channel scales. Ternary mode also writes an ONNX model with reconstructed floating-point weights for standard ONNX Runtime execution; this is not native ternary arithmetic.

Quantize rechecks the source digest and writes provenance.json plus derived-manifest.fragment.json. The registered source manifest is not modified. The fragment records the derived ONNX artifact and any ternary sidecar files; an operator should create a separately versioned manifest before registering derived outputs.

An artifact with format "onnx" can also be selected by the prepare command. The CLI requires exactly one matching artifact unless --artifact ARTIFACT_ID is supplied, rechecks the artifact SHA-256, and requires a self-contained ONNX file (external tensor-data paths are refused).

The current Cmajor preparation path supports only the explicit fallback contracts documented in tools/onnx/README.md:

- FLOAT16 initializers are promoted to FLOAT32.
- Signed INT8 initializers are folded only through initializer-backed DequantizeLinear nodes with explicit scale and optional zero-point.
- Packed ternary UINT8 initializers are decoded only with the cmajor.ternary.<initializer-name> metadata contract.

These conversions expand weights to FLOAT32 Cmajor constants. They do not preserve packed quantized storage, implement GGUF Q4/Q5 quantization, or prove Cmajor compilation / ONNX Runtime parity. Unsupported ONNX operators and known Cmajor template stubs are rejected. Each prepared patch contains provenance.json with the source artifact digest and hashes of generated files.

## Validation States

| Status        | Meaning |
|---------------|---------|
| `unverified`  | Registered but not yet checked |
| `verified`    | Required checks (at least SHA-256) have passed |
| `quarantined` | Failed a check or marked suspicious; not eligible for deployment |
| `failed`      | Explicitly rejected |

A model or artifact in `quarantined` or `failed` state must not be deployed by default.

---

## Example (Minimal)

```json
{
  "manifest_version": "1.0",
  "id": "example/phi-3.5-mini",
  "name": "Phi-3.5 Mini Instruct",
  "version": "2024-10-01",
  "publisher": "Microsoft",
  "description": "Small instruction-tuned model",
  "license": {
    "spdx": "MIT",
    "name": "MIT License"
  },
  "source": {
    "upstream_repo": "https://huggingface.co/microsoft/Phi-3.5-mini-instruct",
    "retrieved_at": "2026-11-18T12:00:00Z"
  },
  "artifacts": [
    {
      "id": "phi-3.5-mini-q4km",
      "role": "quantized",
      "format": "gguf",
      "filename": "Phi-3.5-mini-instruct-Q4_K_M.gguf",
      "sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
      "quantization": {
        "method": "Q4_K_M",
        "tool": "llama.cpp"
      },
      "supported_backends": ["llama.cpp"],
      "validation": {
        "status": "unverified"
      }
    }
  ]
}
```

---

## Next Steps for M1

- Finalize the JSON Schema
- Implement local registry storage that stores manifests + artifact metadata
- Provide CLI commands: `register`, `inspect`, `list`, `verify` (hash check)
- Reject deployment of any artifact whose validation status is not `verified`

Later milestones will extend the manifest with richer preparation and runtime records.