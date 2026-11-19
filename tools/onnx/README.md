# ONNX-to-Cmajor preparation

This toolchain is integrated from the merged implementation in ljrseals-dev/schema (ONNX emitter fallback work, PRs #7 and #8), together with the matching Cmajor patch templates from cmajor-lang/cmajor.

## Supported preparation

The emitter accepts a deliberately narrow ONNX operator set and applies only explicit, metadata-backed initializer rewrites:

- FLOAT16 initializers and tensor constants are promoted to FLOAT32. FLOAT16 graph inputs/outputs are refused because this path does not insert runtime cast adapters.
- Signed INT8 initializer weights are dequantized only when they have an initializer-backed ONNX DequantizeLinear node with explicit scale and optional zero-point. Scalar and one-dimensional per-axis scales are supported; dynamic scales, unsigned INT8, mixed consumers, and graph-boundary quantized tensors are refused.
- Packed ternary initializers are decoded only when the model includes a cmajor.ternary.<initializer-name> metadata contract with encoding, logical shape, bit order, and all three codebook values. Reserved symbols, invalid padding, missing metadata, and malformed contracts are refused.

**Important:** this is a conversion fallback, not a compression-preserving Cmajor runtime. The generated Cmajor source embeds FLOAT32 constants. It does not produce new GGUF quantization, retain INT8/ternary packed weights in the generated Cmajor patch, or prove a memory/performance benefit.

## Prepare from the registry

Install the optional Python dependencies:

```sh
python3 -m pip install -r tools/onnx/requirements.txt
```

Register a manifest with one ONNX artifact, download it, and verify its digest:

```sh
bash cli/llm-models register path/to/model.manifest.json
bash cli/llm-models pull https://example.org/model.onnx --sha256 <64-hex-sha256> --filename model.onnx
bash cli/llm-models prepare publisher/model
```

If the manifest has multiple ONNX artifacts, select one explicitly:

```sh
bash cli/llm-models prepare publisher/model --artifact onnx-fp16
```

By default the patch is written under registry/prepared/<model-id-with-slashes-replaced>. A custom, new output path can be supplied with --output. Existing output directories are not overwritten. The CLI rechecks the artifact SHA-256 immediately before conversion.

The output contains model.cmajor, onnx.cmajor, model.cmajorpatch, and provenance.json. Provenance records the source model ID, artifact ID, source digest, observed quantized tensor counts, transformations, and SHA-256 digests of generated files.

## Direct tool use

```sh
python3 tools/onnx/prepare_model.py \
  --model path/to/model.onnx \
  --output path/to/new-cmajor-patch \
  --model-id publisher/model \
  --artifact-id onnx-fp16 \
  --sha256 <64-hex-sha256>
```

The wrapper refuses external ONNX tensor-data references. This avoids following paths embedded in an untrusted ONNX file outside the verified artifact. Package external tensor data into a supported self-contained ONNX artifact before preparation.

## Tests and acceptance boundary

```sh
python3 -m pip install -r tools/onnx/requirements.txt
python3 tools/onnx/test_fallback.py
python3 tools/onnx/test_prepare.py
bash tools/onnx/test_cli_prepare.sh
```

The tests cover numeric fallback transforms, INT8 per-axis dequantization, packed ternary decoding, malformed/unsupported cases, hash refusal, patch generation, provenance hashes, and the registry CLI lifecycle.

The tests do **not** prove that generated Cmajor compiles, that all model operators are supported, or that Cmajor execution matches ONNX Runtime. A Cmajor compiler/runtime and ONNX Runtime parity suite remain separate acceptance gates. Unsupported operators are rejected rather than approximated.

## Licensing

See LICENSE.md in this directory. The Cmajor emitter and templates retain their upstream Cmajor Software Ltd copyright and GPL-3.0-or-later/commercial licensing. The numeric fallback runtime is separately sourced from ljrseals-dev/schema and is covered by that repository's MIT licence.
