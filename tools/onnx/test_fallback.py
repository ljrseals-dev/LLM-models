"""Focused integration tests for the ONNX emitter's explicit fallback rewrites.

Run with: python -m pip install -r tools/onnx/requirements.txt
          python tools/onnx/test_fallback.py
"""
import importlib.util
import unittest
from pathlib import Path

import numpy as np
import onnx
from onnx import TensorProto, helper, numpy_helper

SCRIPT = Path(__file__).with_name("onnxToCmajor.py")
SPEC = importlib.util.spec_from_file_location("onnx_to_cmajor", SCRIPT)
EMITTER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EMITTER)


def tensor_value_info(name, elem_type, shape):
    return helper.make_tensor_value_info(name, elem_type, shape)


class QuantizedEmitterTests(unittest.TestCase):
    def model(self, nodes, initializers, outputs, metadata=None, value_info=None):
        graph = helper.make_graph(
            nodes, "fallback-test", [], outputs,
            initializer=initializers, value_info=value_info or [],
        )
        model = helper.make_model(
            graph, opset_imports=[helper.make_opsetid("", 13)],
        )
        for key, value in (metadata or {}).items():
            item = model.metadata_props.add()
            item.key, item.value = key, value
        return model

    def test_float16_initializer_promoted(self):
        weight = numpy_helper.from_array(np.array([1.5, -2.0], dtype=np.float16), name="weight")
        model = self.model([], [weight], [])
        EMITTER.prepare_quantized_model(model)
        result = numpy_helper.to_array(model.graph.initializer[0])
        self.assertEqual(model.graph.initializer[0].data_type, TensorProto.FLOAT)
        np.testing.assert_array_equal(result, np.array([1.5, -2.0], dtype=np.float32))

    def test_int8_dequantize_linear_folded(self):
        q = numpy_helper.from_array(np.array([-4, 0, 8], dtype=np.int8), name="q")
        scale = numpy_helper.from_array(np.array(0.25, dtype=np.float32), name="scale")
        zero = numpy_helper.from_array(np.array(0, dtype=np.int8), name="zero")
        dq = helper.make_node("DequantizeLinear", ["q", "scale", "zero"], ["deq"], name="dq")
        output = tensor_value_info("deq", TensorProto.FLOAT, [3])
        model = self.model([dq], [q, scale, zero], [output])
        EMITTER.prepare_quantized_model(model)
        self.assertFalse(any(n.op_type == "DequantizeLinear" for n in model.graph.node))
        self.assertEqual(model.graph.output[0].name, "q")
        self.assertEqual(model.graph.initializer[0].data_type, TensorProto.FLOAT)
        np.testing.assert_allclose(
            numpy_helper.to_array(model.graph.initializer[0]), [-1.0, 0.0, 2.0],
        )

    def test_int8_per_axis_dequantization_uses_declared_axis(self):
        q = numpy_helper.from_array(np.array([[-2, 0], [4, 5]], dtype=np.int8), name="q")
        scale = numpy_helper.from_array(np.array([0.5, 0.25], dtype=np.float32), name="scale")
        zero = numpy_helper.from_array(np.array([0, 1], dtype=np.int8), name="zero")
        dq = helper.make_node(
            "DequantizeLinear", ["q", "scale", "zero"], ["deq"],
            name="dq", axis=1,
        )
        output = tensor_value_info("deq", TensorProto.FLOAT, [2, 2])
        model = self.model([dq], [q, scale, zero], [output])
        EMITTER.prepare_quantized_model(model)
        np.testing.assert_allclose(
            numpy_helper.to_array(model.graph.initializer[0]),
            np.array([[-1.0, -0.25], [2.0, 1.0]], dtype=np.float32),
        )

    def test_ternary_requires_and_uses_explicit_contract(self):
        packed = numpy_helper.from_array(np.array([0b00100100], dtype=np.uint8), name="weights")
        contract = (
            '{"encoding":"2bit-packed-v1","shape":[4],"bit_order":"lsb",'
            '"codebook":{"0":-1.0,"1":0.0,"2":1.0}}'
        )
        model = self.model([], [packed], [], {"cmajor.ternary.weights": contract})
        EMITTER.prepare_quantized_model(model)
        self.assertEqual(model.graph.initializer[0].data_type, TensorProto.FLOAT)
        np.testing.assert_array_equal(
            numpy_helper.to_array(model.graph.initializer[0]), [-1.0, 0.0, 1.0, -1.0],
        )

    def test_unannotated_uint8_is_rejected(self):
        packed = numpy_helper.from_array(np.array([0], dtype=np.uint8), name="weights")
        model = self.model([], [packed], [])
        with self.assertRaisesRegex(ValueError, "unsupported quantized tensors remain"):
            EMITTER.prepare_quantized_model(model)

    def test_unknown_operator_is_rejected_before_codegen(self):
        node = helper.make_node("Softmax", ["x"], ["y"], name="unsupported")
        model_input = tensor_value_info("x", TensorProto.FLOAT, [1])
        model_output = tensor_value_info("y", TensorProto.FLOAT, [1])
        graph = helper.make_graph([node], "unsupported-op", [model_input], [model_output])
        model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 13)])
        with self.assertRaisesRegex(ValueError, "unsupported ONNX operator"):
            EMITTER.prepare_quantized_model(model)

    def test_float16_graph_boundary_is_rejected(self):
        model_input = tensor_value_info("x", TensorProto.FLOAT16, [1])
        graph = helper.make_graph([], "boundary", [model_input], [])
        model = helper.make_model(graph)
        with self.assertRaisesRegex(ValueError, "FLOAT16 graph I/O"):
            EMITTER.prepare_quantized_model(model)

    def test_template_stubs_are_rejected_before_codegen(self):
        for op_type, inputs, outputs in (
            ("LSTM", ["x"], ["y"]),
            ("Slice", ["x", "starts", "ends"], ["y"]),
            ("Gather", ["x", "indices"], ["y"]),
            ("Concat", ["x", "y"], ["z"]),
            ("Pad", ["x", "pads"], ["y"]),
            ("GRU", ["x", "w", "r"], ["y", "yh"]),
        ):
            with self.subTest(op_type=op_type):
                node = helper.make_node(op_type, inputs, outputs, name="stub")
                model_input = tensor_value_info("x", TensorProto.FLOAT, [1])
                model_output = tensor_value_info(outputs[0], TensorProto.FLOAT, [1])
                graph = helper.make_graph([node], "stub-op", [model_input], [model_output])
                model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 13)])
                with self.assertRaisesRegex(ValueError, "unsupported ONNX operator"):
                    EMITTER.prepare_quantized_model(model)

    def test_cmajor_conv_infers_kernel_shape_only_for_supported_1d_geometry(self):
        x = tensor_value_info("x", TensorProto.FLOAT, [1, 1, 1, 8])
        y = tensor_value_info("y", TensorProto.FLOAT, [1, 1, 1, 6])
        weights = numpy_helper.from_array(
            np.ones((1, 1, 1, 3), dtype=np.float32), name="weights",
        )
        node = helper.make_node("Conv", ["x", "weights"], ["y"], name="conv")
        graph = helper.make_graph([node], "conv-valid", [x], [y], [weights])
        model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 13)])
        inferred = onnx.shape_inference.infer_shapes(model)
        EMITTER.validate_cmajor_operator_contracts(inferred)
        attrs = {item.name: onnx.helper.get_attribute_value(item) for item in inferred.graph.node[0].attribute}
        self.assertEqual(list(attrs["kernel_shape"]), [1, 3])

    def test_cmajor_conv_rejects_padding_and_bias(self):
        x = tensor_value_info("x", TensorProto.FLOAT, [1, 1, 1, 8])
        y = tensor_value_info("y", TensorProto.FLOAT, [1, 1, 1, 8])
        weights = numpy_helper.from_array(
            np.ones((1, 1, 1, 3), dtype=np.float32), name="weights",
        )
        padded = helper.make_node(
            "Conv", ["x", "weights"], ["y"], name="padded-conv",
            kernel_shape=[1, 3], pads=[0, 1, 0, 1],
        )
        graph = helper.make_graph([padded], "conv-padded", [x], [y], [weights])
        model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 13)])
        inferred = onnx.shape_inference.infer_shapes(model)
        with self.assertRaisesRegex(ValueError, "zero padding"):
            EMITTER.validate_cmajor_operator_contracts(inferred)

        bias = numpy_helper.from_array(np.array([0.0], dtype=np.float32), name="bias")
        with_bias = helper.make_node(
            "Conv", ["x", "weights", "bias"], ["y"], name="biased-conv",
            kernel_shape=[1, 3],
        )
        graph = helper.make_graph([with_bias], "conv-bias", [x], [y], [weights, bias])
        model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 13)])
        inferred = onnx.shape_inference.infer_shapes(model)
        with self.assertRaisesRegex(ValueError, "does not implement the optional bias"):
            EMITTER.validate_cmajor_operator_contracts(inferred)

    def test_cmajor_gemm_rejects_transposed_weights(self):
        a = tensor_value_info("a", TensorProto.FLOAT, [1, 2])
        c_out = tensor_value_info("c", TensorProto.FLOAT, [1, 3])
        b = numpy_helper.from_array(np.ones((3, 2), dtype=np.float32), name="b")
        node = helper.make_node("Gemm", ["a", "b"], ["c"], name="gemm", transB=1)
        graph = helper.make_graph([node], "gemm-transpose", [a], [c_out], [b])
        model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 13)])
        inferred = onnx.shape_inference.infer_shapes(model)
        with self.assertRaisesRegex(ValueError, "transA=transB=0"):
            EMITTER.validate_cmajor_operator_contracts(inferred)

    def test_transpose_uses_onnx_default_reverse_permutation(self):
        model_input = tensor_value_info("x", TensorProto.FLOAT, [2, 3])
        model_output = tensor_value_info("y", TensorProto.FLOAT, [3, 2])
        node = helper.make_node("Transpose", ["x"], ["y"], name="transpose")
        graph = helper.make_graph([node], "transpose-default", [model_input], [model_output])
        model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 13)])
        EMITTER.prepare_quantized_model(model)
        EMITTER.generateNodesAndConnections(model)
        params = EMITTER.getOperatorParameters(node)
        self.assertIn("int[2] (1, 0)", params)


if __name__ == "__main__":
    unittest.main()
