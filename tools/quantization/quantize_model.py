#!/usr/bin/env python3
"""Verified, provenance-recording wrapper around the Realm-Quant algorithms."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import shutil
import sys

import numpy
import onnx

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))
from realm_quant.quantization import quantize_model  # noqa: E402


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def walk_tensors(graph):
    for tensor in graph.initializer:
        yield tensor
    for node in graph.node:
        for attribute in node.attribute:
            if attribute.type == onnx.AttributeProto.TENSOR:
                yield attribute.t
            elif attribute.type == onnx.AttributeProto.TENSORS:
                yield from attribute.tensors
            elif attribute.type == onnx.AttributeProto.GRAPH:
                yield from walk_tensors(attribute.g)
            elif attribute.type == onnx.AttributeProto.GRAPHS:
                for nested in attribute.graphs:
                    yield from walk_tensors(nested)


def reject_external_data(model) -> None:
    external = [
        tensor.name or "<unnamed>"
        for tensor in walk_tensors(model.graph)
        if tensor.data_location == onnx.TensorProto.EXTERNAL or tensor.external_data
    ]
    if external:
        raise ValueError(
            "external ONNX tensor-data references are not supported by this wrapper; "
            "package the source as a self-contained ONNX artifact. Refused: "
            + ", ".join(external)
        )


def version_of(package: str) -> str | None:
    try:
        return importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        return None


def run(args) -> dict:
    source = Path(args.model)
    output_dir = Path(args.output_dir)
    if not source.is_file():
        raise ValueError(f"input ONNX file does not exist or is not regular: {source}")
    if output_dir.exists() or output_dir.is_symlink():
        raise FileExistsError(f"refusing to overwrite existing output directory: {output_dir}")
    if not args.model_id.strip() or not args.artifact_id.strip():
        raise ValueError("model ID and source artifact ID must be non-empty")

    source_hash = sha256_file(source)
    if source_hash != args.sha256.lower():
        raise ValueError(
            f"source SHA-256 mismatch: expected {args.sha256.lower()}, got {source_hash}"
        )

    source_model = onnx.load(str(source), load_external_data=False)
    reject_external_data(source_model)
    onnx.checker.check_model(source_model)

    destination = output_dir / "model.onnx"
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    try:
        result = quantize_model(
            source,
            destination,
            args.mode,
            args.threshold_ratio,
            tuple(item.strip() for item in args.op_types.split(",") if item.strip()),
        )
        if not destination.is_file():
            raise RuntimeError("quantizer did not produce model.onnx")

        candidate = onnx.load(str(destination), load_external_data=False)
        reject_external_data(candidate)
        onnx.checker.check_model(candidate)

        output_files = [destination]
        if args.mode == "ternary":
            output_files.extend(
                [Path(result["sidecar"]), Path(result["manifest"])]
            )
        missing = [str(path) for path in output_files if not path.is_file()]
        if missing:
            raise RuntimeError("quantizer did not produce expected outputs: " + ", ".join(missing))

        output_hashes = {
            path.name: sha256_file(path) for path in output_files
        }
        method = {
            "fp16": "float16-weight-conversion",
            "int8": "dynamic-int8-weight-quantization",
            "ternary": "packed-2bit-ternary-weight-sidecar",
        }[args.mode]
        parameters = {
            "threshold_ratio": args.threshold_ratio if args.mode == "ternary" else None,
            "op_types": [item.strip() for item in args.op_types.split(",") if item.strip()]
            if args.mode == "int8" else None,
        }
        tool_versions = {
            "python": sys.version.split()[0],
            "numpy": numpy.__version__,
            "onnx": onnx.__version__,
            "onnxruntime": version_of("onnxruntime"),
            "onnxconverter-common": version_of("onnxconverter-common"),
        }
        derived_artifacts = []
        for path in output_files:
            derived_id = (
                f"{args.artifact_id}.{args.mode}"
                if path == destination
                else f"{args.artifact_id}.{args.mode}.{path.suffix.lstrip('.')}"
            )
            derived_artifacts.append({
                "id": derived_id,
                "role": "quantized" if path == destination else "other",
                "format": "onnx" if path == destination else "other",
                "filename": path.name,
                "sha256": output_hashes[path.name],
                "quantization": {
                    "method": method,
                    "parent_artifact_id": args.artifact_id,
                    "tool": "realm-quant",
                    "tool_version": "0.1.0",
                    "parameters": {
                        key: value for key, value in parameters.items() if value is not None
                    },
                },
                "validation": {"status": "unverified"},
            })

        fragment = {
            "manifest_fragment_version": "1.0",
            "source_model_id": args.model_id,
            "source_artifact_id": args.artifact_id,
            "source_sha256": source_hash,
            "artifacts": derived_artifacts,
        }
        (output_dir / "derived-manifest.fragment.json").write_text(
            json.dumps(fragment, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

        execution_note = (
            "Packed 2-bit symbols and per-output-channel scales are stored in the NPZ sidecar; "
            "the ONNX model contains reconstructed FLOAT weights for standard ONNX Runtime. "
            "This is not native ternary arithmetic."
            if args.mode == "ternary"
            else (
                "Dynamic weight-only INT8 quantization; operators outside the selected op-types "
                "remain unchanged."
                if args.mode == "int8"
                else "FP16 conversion preserves model I/O tensor types."
            )
        )
        provenance = {
            "provenance_version": "1.0",
            "model_id": args.model_id,
            "source_artifact_id": args.artifact_id,
            "source_format": "onnx",
            "source_sha256": source_hash,
            "quantization_method": method,
            "parameters": parameters,
            "quantizer": "ljrseals-dev/realm-quant",
            "quantizer_source_revision": "05b0db3f28c948e729b9b9586f417cac6537220b",
            "tool_versions": tool_versions,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "execution_note": execution_note,
            "quantizer_report": {
                key: value for key, value in result.items()
                if key not in {"model", "sidecar", "manifest"}
            },
            "output_files_sha256": output_hashes,
            "derived_artifacts": derived_artifacts,
        }
        (output_dir / "provenance.json").write_text(
            json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return provenance
    except Exception:
        if output_dir.exists():
            shutil.rmtree(output_dir)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--artifact-id", required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--mode", choices=("fp16", "int8", "ternary"), required=True)
    parser.add_argument("--threshold-ratio", type=float, default=0.7)
    parser.add_argument("--op-types", default="MatMul,Gemm")
    args = parser.parse_args()
    if len(args.sha256) != 64 or any(ch not in "0123456789abcdefABCDEF" for ch in args.sha256):
        parser.error("--sha256 must contain exactly 64 hexadecimal characters")
    try:
        provenance = run(args)
    except Exception as exc:
        print(f"Quantization refused: {exc}", file=sys.stderr)
        return 2
    print(f"Quantized model artifacts written to: {args.output_dir}")
    print(f"Method: {provenance['quantization_method']}")
    for name, digest in provenance["output_files_sha256"].items():
        print(f"  {name}: {digest}")
    print(provenance["execution_note"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
