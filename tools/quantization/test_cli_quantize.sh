#!/usr/bin/env bash
# End-to-end test for the registry quantize command using a synthetic ONNX graph.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CLI="$ROOT/cli/llm-models"
TMP="$(mktemp -d)"
REGISTRY="$TMP/registry"
FAKE_BIN="$TMP/fake-bin"
mkdir -p "$FAKE_BIN"
cleanup() { rm -rf -- "$TMP"; }
trap cleanup EXIT INT TERM

for tool in jq check-jsonschema python3; do
  command -v "$tool" >/dev/null 2>&1 || {
    printf 'Missing test dependency: %s\n' "$tool" >&2
    exit 2
  }
done

cat > "$FAKE_BIN/curl" <<'CURL'
#!/usr/bin/env bash
set -euo pipefail
out=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output) out="$2"; shift 2 ;;
    *) shift ;;
  esac
done
[[ -n "$out" && -n "${TEST_DOWNLOAD_SOURCE:-}" ]]
cp -- "$TEST_DOWNLOAD_SOURCE" "$out"
CURL
chmod +x "$FAKE_BIN/curl"

export LLM_MODELS_REGISTRY="$REGISTRY"
export TEST_DOWNLOAD_SOURCE="$TMP/fixture.onnx"
python3 - "$TEST_DOWNLOAD_SOURCE" <<'PY'
import sys
import numpy as np
import onnx
from onnx import TensorProto, helper, numpy_helper
path = sys.argv[1]
x = helper.make_tensor_value_info("features", TensorProto.FLOAT, [None, 4])
y = helper.make_tensor_value_info("scores", TensorProto.FLOAT, [None, 4])
weights = np.array([
    [0.25, -0.5, 1.0, 0.4],
    [1.5, 0.2, -0.7, 0.9],
    [-0.4, 0.9, 0.3, -1.1],
    [0.8, -1.2, 0.6, 0.5],
], dtype=np.float32)
weight_tensor = numpy_helper.from_array(weights, name="projection.weight")
node = helper.make_node("MatMul", ["features", "projection.weight"], ["scores"])
graph = helper.make_graph([node], "quantize-cli-fixture", [x], [y], [weight_tensor])
model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 13)])
model.ir_version = 9
onnx.checker.check_model(model)
onnx.save(model, path)
PY

if command -v sha256sum >/dev/null 2>&1; then
  HASH=$(sha256sum "$TEST_DOWNLOAD_SOURCE" | awk '{print $1}')
else
  HASH=$(shasum -a 256 "$TEST_DOWNLOAD_SOURCE" | awk '{print $1}')
fi

jq -n --arg hash "$HASH" '{
  manifest_version:"1.0",
  id:"tests/quantize-cli",
  name:"Quantization CLI fixture",
  version:"1.0.0",
  publisher:"LLM-models tests",
  license:{spdx:"MIT"},
  source:{upstream_repo:"https://example.invalid/fixture"},
  artifacts:[{
    id:"fixture-onnx",
    role:"original",
    format:"onnx",
    filename:"fixture.onnx",
    sha256:$hash,
    validation:{status:"unverified"}
  }]
}' > "$TMP/manifest.json"

bash "$CLI" register "$TMP/manifest.json" >/dev/null
PATH="$FAKE_BIN:$PATH" bash "$CLI" pull https://example.invalid/fixture.onnx \
  --sha256 "$HASH" --filename fixture.onnx >/dev/null

bash "$CLI" quantize tests/quantize-cli --mode ternary --threshold-ratio 0.7 >/dev/null
OUTPUT="$REGISTRY/quantized/tests__quantize-cli/ternary"
[[ -f "$OUTPUT/model.onnx" ]]
[[ -f "$OUTPUT/model.ternary.npz" ]]
[[ -f "$OUTPUT/model.ternary.json" ]]
[[ -f "$OUTPUT/provenance.json" ]]
[[ -f "$OUTPUT/derived-manifest.fragment.json" ]]
jq -e --arg hash "$HASH" '.source_sha256 == $hash and .quantization_method == "packed-2bit-ternary-weight-sidecar"' \
  "$OUTPUT/provenance.json" >/dev/null
jq -e '.artifacts | length == 3' "$OUTPUT/derived-manifest.fragment.json" >/dev/null

if bash "$CLI" quantize tests/quantize-cli --mode ternary --threshold-ratio 0.7 >/dev/null 2>&1; then
  printf 'quantize unexpectedly overwrote an existing output\n' >&2
  exit 1
fi

printf '[PASS] CLI pull -> verified ONNX -> ternary model + packed sidecar + provenance\n'
printf '[PASS] quantize refuses to overwrite existing derived artifacts\n'
