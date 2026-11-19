# LLM-models

> **Local-first model registry and distribution engine**

A verifiable, self-hosted model supply chain: discover, acquire, verify, prepare, and deploy models with explicit provenance and trust.

---

> ⚠️ **CAUTION — REVIEW SAFETY, PROVENANCE, AND LEGAL STATUS BEFORE USE**  
> This repository may contain or link to model-related code, weights, configurations, documentation, or other technical materials whose origin, capabilities, intended use, and downstream effects have not necessarily been independently verified. Do not assume that material is safe, lawful to use, authorized for redistribution, or suitable for deployment merely because it is publicly accessible here.

## Important human-safety warning

The maintainer has raised concerns that technology of this general kind may be connected to government secrecy, coercive use, surveillance, or serious harm to people. Those concerns are a reason to exercise care; **this README does not independently verify any classification, government action, death, or causal connection between a particular technology and harm to any person.** No such allegation should be treated as an established fact without reliable, independently reviewable evidence.

Do not use, adapt, distribute, or combine material from this repository to facilitate:

* violence, threats, intimidation, or physical harm;
* unlawful surveillance, stalking, persecution, or targeting of individuals;
* discrimination, coercion, manipulation, or denial of rights;
* weapons development or operational targeting;
* unauthorized access, credential theft, or other unlawful activity.

Respect human rights, privacy, applicable law, contractual restrictions, and the rights of model, dataset, and software authors.

## Read before downloading, running, or redistributing

1. **Verify provenance.** Identify the original authors, source repositories, model cards, licenses, dataset terms, and cryptographic checksums where available.
2. **Inspect before execution.** Treat scripts, model files, checkpoints, notebooks, containers, and downloaded dependencies as untrusted until reviewed. Use isolated environments and least-privilege permissions.
3. **Check every applicable license.** A model's code license may differ from its weights, training data, tokenizer, or dependencies. Public availability is not a license.
4. **Assess legal restrictions.** Export controls, sanctions, privacy and data-protection laws, intellectual-property rights, sector rules, and platform terms may apply depending on the material, user, location, and intended use.
5. **Validate outputs.** Models can produce inaccurate, biased, unsafe, or harmful results. Human review is required for consequential decisions.
6. **Do not upload sensitive information.** Do not submit confidential, classified, personal, or otherwise restricted information to a model or service unless you are specifically authorized and the environment is approved for that data.

## Disclaimer — no warranty

The repository and any materials made available through it are provided **“AS IS” and “AS AVAILABLE,”** without warranties or conditions of any kind, to the maximum extent permitted by applicable law. This includes, without limitation, warranties of title, non-infringement, merchantability, fitness for a particular purpose, accuracy, security, availability, and freedom from defects.

The maintainer does not warrant that:

* any code, model, weight, dataset, link, or documentation is authentic, complete, current, secure, accurate, or fit for a particular purpose;
* any material is authorized for a particular use or redistribution;
* outputs will be safe, lawful, unbiased, or reliable; or
* the repository complies with every law or regulatory requirement applicable to every user's circumstances.

No technical, legal, safety, or compliance certification is made by this README.

## Limitation of liability and hold harmless

To the maximum extent permitted by applicable law, the repository maintainers and contributors disclaim liability for indirect, incidental, special, consequential, exemplary, or punitive damages, and for loss of data, profits, business, or goodwill arising from access to, use of, inability to use, modification, or redistribution of repository materials.

**By choosing to use or redistribute any material, you are responsible for your own actions and for determining whether your use is lawful and properly authorized.** To the extent permitted by applicable law, you agree to defend and hold harmless the maintainers and contributors from third-party claims, liabilities, damages, and reasonable expenses arising from your misuse of the materials, your violation of law or third-party rights, or your breach of applicable terms.

This provision is not intended to waive rights that cannot legally be waived, exclude liability that cannot legally be excluded, or protect anyone from liability for their own conduct where the law does not permit that result. It is not a substitute for a separately negotiated agreement or advice from a qualified attorney. Merely viewing this public repository does not, by itself, create a contract or guarantee that these terms are enforceable against a visitor.

## Legal and licensing status

This repository's public availability is **not a legal determination** that every file, model, weight, dataset, or use is lawful. The legality of a particular use depends on facts and jurisdiction-specific law. Users must perform their own review and obtain qualified legal advice where appropriate.

A prior license file is not currently present on the default branch as inspected for this README. **No license grant is made by this README.** Unless and until a valid license is added and its scope is confirmed, do not assume permission to copy, modify, distribute, sublicense, or use repository materials beyond rights independently established by law or by the relevant rights holder. Third-party materials remain subject to their own terms.

## Reporting safety, security, rights, or legal concerns

If you identify material that appears to create an immediate risk to a person, do not investigate or confront anyone yourself. Contact appropriate local emergency services or competent authorities when there is an imminent threat.

For repository-related concerns:

* **Security vulnerability:** use GitHub's private vulnerability reporting / Security Advisories feature for this repository if enabled. Do not publish exploit details, credentials, personal data, or sensitive operational information in a public issue.
* **Potentially unlawful or rights-infringing content:** use GitHub's official [reporting and abuse channels](https://support.github.com/) and provide the specific repository path, URL, relevant commit, and a factual explanation.
* **License or provenance concern:** open a concise issue that identifies the exact file or model and provides verifiable source or license evidence. Do not post confidential or classified material.
* **Human-safety concern:** report credible, specific threats to the appropriate competent authority. Preserve relevant public URLs and timestamps; avoid speculation and do not expose victims or private individuals.

Reports should distinguish firsthand evidence from inference, identify dates and affected files, and avoid unsupported accusations. Do not include classified, export-controlled, privileged, or personal information in public GitHub reports.

## Scope and changes

This warning applies to the repository as a whole, including links and materials added later. It does not replace the license or terms governing any third-party component. Repository contents can change; review the relevant file, commit history, and upstream terms each time before use.

---

**Maintainer notice:** This document is a practical safety and risk notice, not legal advice, a finding of fact, a formal compliance report, or a certification that the repository or any proposed use is lawful. Have a qualified attorney review the repository and any intended distribution terms before relying on a disclaimer or hold-harmless provision.

---

## Project Vision

**LLM-models** is intended to become a **local-first model registry and distribution engine**.

It is designed as the model supply chain for self-hosted AI infrastructure:

| Layer              | Responsibility                                      | Owner          |
|--------------------|-----------------------------------------------------|----------------|
| Model registry     | Discover, catalog, version, license, provenance     | LLM-models     |
| Artifact manager   | Download, cache, resume, content-addressed storage  | LLM-models     |
| Trust & validation | Hashes, signatures, format checks, quarantine       | LLM-models     |
| Preparation        | Quantization, conversion, derived-artifact records  | LLM-models     |
| Runtime            | Local inference backends, lifecycle, health         | LLM-models     |
| Host infrastructure| Provisioning, LEMP, security, firewall              | StackAlign     |
| Integration        | Optional, narrow service contract                   | Companion      |

### Design Principles

- **Local-first**: No mandatory cloud provider or proprietary marketplace.
- **Verifiable**: Models are never considered verified merely because they downloaded.
- **Explicit**: Deployment, quantization, and network exposure require deliberate action.
- **Reproducible**: Derived artifacts (e.g. quantizations) record source hash, tool, parameters, and output hash.
- **Backend-independent**: Start with llama.cpp (GGUF) and ONNX Runtime; support additional backends via adapters.
- **Safe defaults**: Loopback-only inference by default; no automatic public exposure; quarantine on failed validation.

### Proposed CLI Surface (target)

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

These commands describe the intended user experience. The current quantize command supports FP16, dynamic INT8, and packed 2-bit ternary sidecars for ONNX. The separate prepare command converts supported ONNX graphs to Cmajor; GGUF Q4_K_M quantization remains future work.

### Artifact Lifecycle

```
DISCOVERED → DOWNLOADED → VERIFIED → PREPARED → VALIDATED → DEPLOYED → HEALTH_CHECKED
```

A failed validation stops deployment. A failed health check must not silently replace a working model.

### What this project will not do

- Automatically download models during ordinary StackAlign installation.
- Trust a model merely because it comes from a popular hosting service.
- Bundle model weights into the application repository.
- Silently quantize or replace a model.
- Expose an inference API on a public interface by default.
- Claim that a model is safe, unbiased, licensed for every use, or suitable for production simply because validation checks passed.

---

## Current Status

| Milestone / Deliverable              | Status                          |
|--------------------------------------|---------------------------------|
| Safety / legal README                | Present                         |
| Project vision and architecture      | Documented (`docs/VISION.md`)   |
| Model manifest specification         | Draft (`docs/MANIFEST.md`)      |
| JSON Schema                          | Present                         |
| Local registry layout                | Implemented (`registry/`)       |
| CLI: list, inspect, register, status | Implemented                     |
| HTTPS download (`pull`) + optional SHA-256 verification | Implemented; resumable partials |
| Content-addressed storage + quarantine | Implemented; immutable hashes  |
| Manifest schema validation           | Implemented; fails closed       |
| Isolated regression tests + CI        | Implemented                     |
| Audit log                            | Basic append-only local log     |
| ONNX quantization (M3) | Implemented: FP16, dynamic INT8, packed 2-bit ternary sidecars; ternary ONNX model reconstructs float weights |
| ONNX-to-Cmajor preparation (M3) | Implemented for explicit FLOAT16, signed INT8 DQ, and metadata-declared ternary cases; expands weights to FLOAT32 |
| Runtime / deployment (M4)            | Scaffold only                   |
| Multi-backend (M5)                   | Not started                     |
| StackAlign integration (M6)          | Spec only (`docs/INTEGRATION.md`)|

The `quantize` command uses the merged Python workbench from `ljrseals-dev/realm-quant` to produce FP16, dynamic INT8, or packed 2-bit ternary weight artifacts. Ternary mode emits a compact NPZ sidecar with per-output-channel scales and an ONNX model with reconstructed floating-point weights for standard ONNX Runtime compatibility. Each run writes source/output hashes, tool versions, quantization parameters, and a derived-manifest fragment; it does not mutate the registered source manifest.

The `prepare` command converts a verified, self-contained ONNX artifact into a Cmajor patch using the quantized fallback work integrated from `ljrseals-dev/schema`. It records source and output hashes in `provenance.json`, refuses unsupported operators and external ONNX tensor-data paths, and never overwrites an existing output. The supported fallbacks promote FLOAT16, fold explicit signed INT8 `DequantizeLinear` weights, and decode metadata-declared packed ternary weights. **These Cmajor fallbacks expand supported weights to FLOAT32 constants; they are not a compression-preserving runtime.** The separate Realm-Quant ternary sidecar is not yet consumed by the Cmajor emitter, and dynamic INT8 operators may be outside its operator allowlist. Generated Cmajor compilation and ONNX Runtime parity are not yet verified.

The `deploy` and `rollback` commands remain deliberately unimplemented and return a nonzero status without changing services.

Legacy installer scripts (Scholar AI, Termux llama.cpp) live under `contrib/` as historical examples only; they are not part of the supported registry CLI.

### Quick start (local)

```bash
# From the repository root
# Registry tools: bash, jq, check-jsonschema, curl or wget,
# and sha256sum or shasum.
# Optional ONNX preparation tools:
python3 -m pip install -r tools/onnx/requirements.txt
python3 -m pip install -r tools/quantization/requirements.txt
bash cli/llm-models status
bash cli/llm-models register examples/phi-3.5-mini.example.manifest.json
bash cli/llm-models list
bash cli/llm-models inspect example/phi-3.5-mini
# For a manifest containing a verified ONNX artifact:
bash cli/llm-models quantize publisher/model --mode int8 --artifact onnx-artifact-id
bash cli/llm-models prepare publisher/model --artifact onnx-artifact-id
bash scripts/smoke-test.sh
```

See also:

- [`docs/VISION.md`](docs/VISION.md) — full architectural recommendation  
- [`docs/MANIFEST.md`](docs/MANIFEST.md) — model manifest specification  
- [`docs/ROADMAP.md`](docs/ROADMAP.md) — milestone tracking  
- [`docs/INTEGRATION.md`](docs/INTEGRATION.md) — StackAlign contract notes  
- [`tools/onnx/README.md`](tools/onnx/README.md) — ONNX-to-Cmajor fallback preparation, CLI use, tests, and licensing  
- [`tools/quantization/README.md`](tools/quantization/README.md) — FP16, dynamic INT8, ternary quantization, and provenance
- [`schemas/model-manifest.schema.json`](schemas/model-manifest.schema.json)  

---

## Relationship to StackAlign

StackAlign is a separate project focused on guarded LEMP installation and host operations for EL-family Linux systems. It deliberately excludes AI/ML tooling from its core.

The intended relationship is:

- **StackAlign** owns the host and infrastructure.
- **LLM-models** owns the models.
- A narrow, optional integration contract allows StackAlign-managed hosts to discover and consume a locally running model service without embedding model logic in StackAlign itself.

This separation preserves StackAlign’s security model and scope while enabling a coherent self-hosted AI infrastructure ecosystem.

---

## Contributing / Development Notes

- Prefer small, reviewable changes.
- Manifest and verification correctness are higher priority than feature breadth.
- Do not introduce automatic network exposure or silent model mutation.
- Keep the safety posture of this README intact.