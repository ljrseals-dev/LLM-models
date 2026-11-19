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


def quantized_model_with_dequantize_attribute(attribute_name: str, attribute_value: int) -> onnx.ModelProto:
    q = helper.make_tensor("q", TensorProto.INT8, [1], [4])
    scale = helper.make_tensor("scale", TensorProto.FLOAT, [], [0.5])
    zero = helper.make_tensor("zero", TensorProto.INT8, [], [0])
    node = helper.make_node(
        "DequantizeLinear", ["q", "scale", "zero"], ["weight"],
        **{attribute_name: attribute_value},
    )
    graph = helper.make_graph([node], "quantized", [], [], initializer=[q, scale, zero])
    return helper.make_model(graph, opset_imports=[helper.make_opsetid("", 21)])


class NestedExternalTensorTests(unittest.TestCase):
    def test_rejects_external_tensor_inside_graph_attribute(self):
        model = model_with_nested_tensor(external=True)
        with self.assertRaisesRegex(ValueError, "nested_weight"):
            onnxToCmajor.reject_external_data(model)

    def test_accepts_self_contained_tensor_inside_graph_attribute(self):
        model = model_with_nested_tensor(external=False)
        onnxToCmajor.reject_external_data(model)

    def test_rejects_block_quantized_dequantize_linear(self):
        model = quantized_model_with_dequantize_attribute("block_size", 1)
        with self.assertRaisesRegex(ValueError, "blocked INT8 quantization"):
            onnxToCmajor._dequantize_int8_initializers(model)

    def test_rejects_non_float32_dequantize_output(self):
        model = quantized_model_with_dequantize_attribute("output_dtype", TensorProto.FLOAT16)
        with self.assertRaisesRegex(ValueError, "only FLOAT32"):
            onnxToCmajor._dequantize_int8_initializers(model)


if __name__ == "__main__":
    unittest.main()
