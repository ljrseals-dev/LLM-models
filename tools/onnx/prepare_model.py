#!/usr/bin/env python3
"""Prepare a verified ONNX artifact as a Cmajor patch.

The quantized fallback transformations are reused from schema_review and the
Cmajor emitter. Output is fail-closed and includes a provenance.json record.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys

import onnx
from onnx import TensorProto, shape_inference

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import onnxToCmajor as emitter  # noqa: E402


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _walk_graph_tensors(graph):
    for tensor in graph.initializer:
        yield tensor
    for node in graph.node:
        for attribute in node.attribute:
            if attribute.type == onnx.AttributeProto.TENSOR:
                yield attribute.t
            elif attribute.type == onnx.AttributeProto.TENSORS:
                yield from attribute.tensors
            elif attribute.type == onnx.AttributeProto.GRAPH:
                yield from _walk_graph_tensors(attribute.g)
            elif attribute.type == onnx.AttributeProto.GRAPHS:
                for nested in attribute.graphs:
                    yield from _walk_graph_tensors(nested)


def reject_external_data(model) -> None:
    external = [
        tensor.name or "<unnamed>"
        for tensor in _walk_graph_tensors(model.graph)
        if tensor.data_location == TensorProto.EXTERNAL or tensor.external_data
    ]
    if external:
        raise ValueError(
            "external ONNX tensor data is not supported by this preparation path; "
            "package the model as a self-contained ONNX artifact. Refused tensors: "
            + ", ".join(external)
        )


def reset_emitter_state() -> None:
    for name in ("ioBlock", "nodes", "connections", "initialisers", "outputNames"):
        getattr(emitter, name).clear()
    for name in ("endpoints", "connectionDataTypes"):
        getattr(emitter, name).clear()


def tensor_type_counts(model) -> dict[str, int]:
    counts = {
        "float16_initializers": 0,
        "int8_initializers": 0,
        "uint8_initializers": 0,
        "dequantize_linear_nodes": 0,
        "annotated_ternary_initializers": 0,
    }
    for tensor in model.graph.initializer:
        if tensor.data_type == TensorProto.FLOAT16:
            counts["float16_initializers"] += 1
        elif tensor.data_type == TensorProto.INT8:
            counts["int8_initializers"] += 1
        elif tensor.data_type == TensorProto.UINT8:
            counts["uint8_initializers"] += 1
    counts["dequantize_linear_nodes"] = sum(
        node.op_type == "DequantizeLinear" for node in model.graph.node
    )
    counts["annotated_ternary_initializers"] = sum(
        item.key.startswith("cmajor.ternary.") for item in model.metadata_props
    )
    return counts


def prepare(args) -> dict:
    source = Path(args.model)
    output = Path(args.output)
    if not source.is_file():
        raise ValueError(f"input ONNX file does not exist or is not a regular file: {source}")
    if output.exists() or output.is_symlink():
        raise FileExistsError(f"refusing to overwrite existing output: {output}")
    if not args.model_id.strip() or not args.artifact_id.strip():
        raise ValueError("model ID and artifact ID must be non-empty")

    source_hash = sha256_file(source)
    if source_hash != args.sha256.lower():
        raise ValueError(
            f"input SHA-256 mismatch: expected {args.sha256.lower()}, got {source_hash}"
        )

    # Do not let untrusted ONNX external_data locations cause reads outside the
    # verified artifact. This path accepts a single self-contained ONNX file.
    model = onnx.load(str(source), load_external_data=False)
    reject_external_data(model)
    onnx.checker.check_model(model)
    input_counts = tensor_type_counts(model)

    emitter.prepare_quantized_model(model)
    inferred = shape_inference.infer_shapes(model)
    onnx.checker.check_model(inferred)

    output.parent.mkdir(parents=True, exist_ok=True)
    reset_emitter_state()
    try:
        emitter.generateNodesAndConnections(inferred)
        emitter.printCmajor(str(output))
        required = ("model.cmajor", "onnx.cmajor", "model.cmajorpatch")
        missing = [name for name in required if not (output / name).is_file()]
        if missing:
            raise RuntimeError("Cmajor emitter did not create required files: " + ", ".join(missing))

        output_hashes = {name: sha256_file(output / name) for name in required}
        transformations = []
        if input_counts["float16_initializers"]:
            transformations.append("FLOAT16 initializers promoted to FLOAT32")
        if input_counts["int8_initializers"] or input_counts["dequantize_linear_nodes"]:
            transformations.append("explicit initializer-backed INT8 DequantizeLinear folded to FLOAT32")
        if input_counts["annotated_ternary_initializers"]:
            transformations.append("metadata-declared packed ternary weights decoded to FLOAT32")
        if not transformations:
            transformations.append("no quantized initializer fallback was required")

        provenance = {
            "provenance_version": "1.0",
            "model_id": args.model_id,
            "source_artifact_id": args.artifact_id,
            "source_format": "onnx",
            "source_sha256": source_hash,
            "converter": "LLM-models ONNX-to-Cmajor preparation",
            "emitter": "Cmajor onnxToCmajor.py with schema_review fallback_runtime",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "input_tensor_counts": input_counts,
            "transformations": transformations,
            "output_format": "cmajor-patch",
            "output_files_sha256": output_hashes,
            "weights_representation": "FLOAT32 constants in generated Cmajor source",
            "cmajor_compilation_verified": False,
            "onnx_runtime_parity_verified": False,
        }
        temporary = output / ".provenance.json.tmp"
        temporary.write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temporary.replace(output / "provenance.json")
        return provenance
    except Exception:
        if output.exists():
            shutil.rmtree(output)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, help="self-contained, verified ONNX model file")
    parser.add_argument("--output", required=True, help="new output directory; existing paths are refused")
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--artifact-id", required=True)
    parser.add_argument("--sha256", required=True)
    args = parser.parse_args()
    if len(args.sha256) != 64 or any(ch not in "0123456789abcdefABCDEF" for ch in args.sha256):
        parser.error("--sha256 must contain exactly 64 hexadecimal characters")
    try:
        provenance = prepare(args)
    except (OSError, ValueError, RuntimeError, onnx.checker.ValidationError) as exc:
        print(f"Preparation refused: {exc}", file=sys.stderr)
        return 2
    print(f"Prepared Cmajor patch: {args.output}")
    print("Transformations:")
    for item in provenance["transformations"]:
        print(f"  - {item}")
    print("Note: generated Cmajor compilation and ONNX Runtime parity are not claimed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
