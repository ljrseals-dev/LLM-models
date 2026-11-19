"""End-to-end tests for the verified ONNX-to-Cmajor preparation wrapper."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import numpy as np
import onnx
from onnx import TensorProto, helper, numpy_helper

ROOT = Path(__file__).resolve().parents[2]
PREPARE = ROOT / "tools" / "onnx" / "prepare_model.py"


def make_quantized_model(path: Path) -> None:
    x = helper.make_tensor_value_info("x", TensorProto.FLOAT, [1, 2])
    y = helper.make_tensor_value_info("y", TensorProto.FLOAT, [1, 1])
    q = numpy_helper.from_array(np.array([[-4], [8]], dtype=np.int8), name="q")
    scale = numpy_helper.from_array(np.array(0.25, dtype=np.float32), name="scale")
    zero = numpy_helper.from_array(np.array(0, dtype=np.int8), name="zero")
    dq = helper.make_node("DequantizeLinear", ["q", "scale", "zero"], ["deq"], name="dequantize")
    matmul = helper.make_node("MatMul", ["x", "deq"], ["y"], name="matmul")
    graph = helper.make_graph([dq, matmul], "quantized-fixture", [x], [y],
                              initializer=[q, scale, zero])
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 13)])
    onnx.checker.check_model(model)
    onnx.save(model, path)


class PrepareModelTests(unittest.TestCase):
    def run_prepare(self, source: Path, output: Path, digest: str):
        return subprocess.run(
            [
                sys.executable, str(PREPARE),
                "--model", str(source),
                "--output", str(output),
                "--model-id", "tests/quantized-fixture",
                "--artifact-id", "fixture-onnx",
                "--sha256", digest,
            ],
            text=True, capture_output=True, check=False,
        )

    def test_verified_int8_model_emits_patch_and_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "fixture.onnx"
            output = root / "prepared"
            make_quantized_model(source)
            digest = hashlib.sha256(source.read_bytes()).hexdigest()

            result = self.run_prepare(source, output, digest)
            self.assertEqual(result.returncode, 0, result.stderr)
            for name in ("model.cmajor", "onnx.cmajor", "model.cmajorpatch", "provenance.json"):
                self.assertTrue((output / name).is_file(), name)

            provenance = json.loads((output / "provenance.json").read_text())
            self.assertEqual(provenance["source_sha256"], digest)
            self.assertEqual(provenance["source_artifact_id"], "fixture-onnx")
            self.assertFalse(provenance["cmajor_compilation_verified"])
            self.assertFalse(provenance["onnx_runtime_parity_verified"])
            self.assertIn(
                "explicit initializer-backed INT8 DequantizeLinear folded to FLOAT32",
                provenance["transformations"],
            )
            for name, expected in provenance["output_files_sha256"].items():
                actual = hashlib.sha256((output / name).read_bytes()).hexdigest()
                self.assertEqual(actual, expected)

    def test_hash_mismatch_refuses_preparation_without_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "fixture.onnx"
            output = root / "prepared"
            make_quantized_model(source)
            result = self.run_prepare(source, output, "0" * 64)
            self.assertEqual(result.returncode, 2)
            self.assertIn("SHA-256 mismatch", result.stderr)
            self.assertFalse(output.exists())

    def test_existing_output_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "fixture.onnx"
            output = root / "prepared"
            make_quantized_model(source)
            output.mkdir()
            sentinel = output / "keep.txt"
            sentinel.write_text("do not overwrite")
            digest = hashlib.sha256(source.read_bytes()).hexdigest()

            result = self.run_prepare(source, output, digest)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(sentinel.read_text(), "do not overwrite")


if __name__ == "__main__":
    unittest.main()
