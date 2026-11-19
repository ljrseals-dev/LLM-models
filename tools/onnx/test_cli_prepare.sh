#!/usr/bin/env bash
# End-to-end test for the public CLI prepare command; all inputs are synthetic.
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
x = helper.make_tensor_value_info("x", TensorProto.FLOAT, [1, 2])
y = helper.make_tensor_value_info("y", TensorProto.FLOAT, [1, 1])
q = numpy_helper.from_array(np.array([[-4], [8]], dtype=np.int8), name="q")
scale = numpy_helper.from_array(np.array(0.25, dtype=np.float32), name="scale")
zero = numpy_helper.from_array(np.array(0, dtype=np.int8), name="zero")
dq = helper.make_node("DequantizeLinear", ["q", "scale", "zero"], ["deq"], name="dequantize")
matmul = helper.make_node("MatMul", ["x", "deq"], ["y"], name="matmul")
graph = helper.make_graph([dq, matmul], "cli-fixture", [x], [y],
                          initializer=[q, scale, zero])
model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 13)])
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
  id:"tests/quantized-cli",
  name:"Quantized ONNX CLI fixture",
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

bash "$CLI" prepare tests/quantized-cli >/dev/null
OUTPUT="$REGISTRY/prepared/tests__quantized-cli"
[[ -f "$OUTPUT/model.cmajor" ]]
[[ -f "$OUTPUT/onnx.cmajor" ]]
[[ -f "$OUTPUT/model.cmajorpatch" ]]
[[ -f "$OUTPUT/provenance.json" ]]
jq -e --arg hash "$HASH" '.source_sha256 == $hash and .cmajor_compilation_verified == false' \
  "$OUTPUT/provenance.json" >/dev/null

if bash "$CLI" prepare tests/quantized-cli >/dev/null 2>&1; then
  printf 'prepare unexpectedly overwrote an existing output\n' >&2
  exit 1
fi

printf '[PASS] CLI pull -> verified ONNX -> Cmajor patch + provenance\n'
printf '[PASS] prepare refuses to overwrite an existing patch\n'
