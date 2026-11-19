import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import numpy as np
import pytest

from realm_quant.quantization import _ternarize, pack_2bit, unpack_2bit, quantize_model


def test_pack_unpack_round_trip_all_symbols():
    values = np.array([0, 1, 2, 3, 2, 1, 0, 3, 1], dtype=np.uint8)
    packed = pack_2bit(values)
    np.testing.assert_array_equal(unpack_2bit(packed, values.size), values)


def test_pack_rejects_out_of_range_symbols():
    with pytest.raises(ValueError):
        pack_2bit(np.array([4], dtype=np.uint8))


def test_ternary_values_are_only_zero_or_signed_scale():
    weights = np.array(
        [[1.0, -2.0, 0.0, 4.0], [-1.0, 3.0, -5.0, 2.0]],
        dtype=np.float32,
    )
    symbols, scales, restored = _ternarize(weights, 0.5)
    assert set(np.unique(symbols)).issubset({0, 1, 2})
    assert scales.shape == (2,)
    assert np.isfinite(restored).all()
    assert np.all(np.isin(restored, [-scales[0], 0.0, scales[0], -scales[1], scales[1]]))


def test_ternary_rejects_nonfinite_weights():
    with pytest.raises(ValueError):
        _ternarize(np.array([[1.0, np.nan]], dtype=np.float32), 0.7)


def test_ternary_requires_matrix_or_higher_rank():
    with pytest.raises(ValueError):
        _ternarize(np.array([1.0, 2.0], dtype=np.float32), 0.7)


def test_pack_rejects_values_that_would_wrap_to_valid_symbols():
    for values in ([256], [-1], [1.5], [True]):
        with pytest.raises(ValueError):
            pack_2bit(values)


def test_unpack_rejects_non_byte_values_and_non_integer_count():
    for packed, count in (([256], 1), ([-1], 1), ([1.5], 1), ([0], 1.5)):
        with pytest.raises(ValueError):
            unpack_2bit(packed, count)


def test_quantizer_rejects_external_tensor_data_in_nested_graph(tmp_path):
    import onnx
    from onnx import TensorProto, helper

    tensor = helper.make_tensor("nested_weight", TensorProto.FLOAT, [1], [1.0])
    tensor.data_location = TensorProto.EXTERNAL
    entry = tensor.external_data.add()
    entry.key = "location"
    entry.value = "../../outside.bin"
    nested = helper.make_graph([], "nested-branch", [], [], initializer=[tensor])
    empty = helper.make_graph([], "empty-branch", [], [])
    condition = helper.make_tensor_value_info("condition", TensorProto.BOOL, [])
    output = helper.make_tensor_value_info("result", TensorProto.FLOAT, [1])
    node = helper.make_node("If", ["condition"], ["result"],
                            then_branch=nested, else_branch=empty)
    graph = helper.make_graph([node], "outer", [condition], [output])
    model = helper.make_model(graph)
    source = tmp_path / "external.onnx"
    destination = tmp_path / "quantized.onnx"
    source.write_bytes(model.SerializeToString())

    with pytest.raises(ValueError, match="nested_weight"):
        quantize_model(source, destination, "fp16")
    assert not destination.exists()


def test_quantizer_refuses_to_overwrite_source(tmp_path):
    source = tmp_path / "model.onnx"
    source.write_bytes(b"not an ONNX model")
    with pytest.raises(ValueError, match="source and destination"):
        quantize_model(source, source, "fp16")
