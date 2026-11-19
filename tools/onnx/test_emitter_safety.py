"""Safety regressions for ONNX tensors nested in graph-valued attributes."""
from __future__ import annotations

import sys
from pathlib import Path
import unittest

import onnx
from onnx import TensorProto, helper

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "onnx"))
import onnxToCmajor  # noqa: E402


def model_with_nested_tensor(external: bool) -> onnx.ModelProto:
    tensor = helper.make_tensor("nested_weight", TensorProto.FLOAT, [1], [1.0])
    if external:
        tensor.data_location = TensorProto.EXTERNAL
        entry = tensor.external_data.add()
        entry.key = "location"
        entry.value = "../../outside.bin"
    nested = helper.make_graph([], "nested-branch", [], [], initializer=[tensor])
    empty = helper.make_graph([], "empty-branch", [], [])
    condition = helper.make_tensor_value_info("condition", TensorProto.BOOL, [])
    output = helper.make_tensor_value_info("result", TensorProto.FLOAT, [1])
    node = helper.make_node(
        "If", ["condition"], ["result"],
        then_branch=nested, else_branch=empty,
    )
    graph = helper.make_graph([node], "outer", [condition], [output])
    return helper.make_model(graph)


class NestedExternalTensorTests(unittest.TestCase):
    def test_rejects_external_tensor_inside_graph_attribute(self):
        model = model_with_nested_tensor(external=True)
        with self.assertRaisesRegex(ValueError, "nested_weight"):
            onnxToCmajor.reject_external_data(model)

    def test_accepts_self_contained_tensor_inside_graph_attribute(self):
        model = model_with_nested_tensor(external=False)
        onnxToCmajor.reject_external_data(model)


if __name__ == "__main__":
    unittest.main()
