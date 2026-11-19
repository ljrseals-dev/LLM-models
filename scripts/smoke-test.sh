#!/usr/bin/env bash
# Isolated regression tests for the M1/M2 CLI. No real network access is used.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLI="$ROOT/cli/llm-models"
TMP="$(mktemp -d)"
REGISTRY="$TMP/registry"
FAKE_BIN="$TMP/fake-bin"
mkdir -p "$FAKE_BIN"
cleanup() { rm -rf -- "$TMP"; }
trap cleanup EXIT INT TERM

for tool in jq check-jsonschema; do
  command -v "$tool" >/dev/null 2>&1 || {
    printf 'Missing test dependency: %s\n' "$tool" >&2
    exit 2
  }
done
if ! command -v sha256sum >/dev/null 2>&1 && ! command -v shasum >/dev/null 2>&1; then
  printf 'Missing test dependency: sha256sum or shasum\n' >&2
  exit 2
fi

pass() { printf '[PASS] %s\n' "$1"; }
fail() { printf '[FAIL] %s\n' "$1" >&2; exit 1; }
expect_fail() {
  local label="$1"
  shift
  if "$@" >/dev/null 2>&1; then fail "$label (unexpected success)"; fi
  pass "$label"
}

export LLM_MODELS_REGISTRY="$REGISTRY"

# A fake curl copies a local fixture to the requested output path. It exercises
# the CLI's downloader path without reaching the network.
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

printf 'fixture model weights\n' > "$TMP/payload.gguf"
if command -v sha256sum >/dev/null 2>&1; then
  HASH=$(sha256sum "$TMP/payload.gguf" | awk '{print $1}')
else
  HASH=$(shasum -a 256 "$TMP/payload.gguf" | awk '{print $1}')
fi

jq -n --arg hash "$HASH" '{
  manifest_version:"1.0",
  id:"tests/fixture-model",
  name:"Fixture model",
  version:"1.0.0",
  publisher:"LLM-models tests",
  license:{spdx:"MIT"},
  source:{upstream_repo:"https://example.invalid/fixture"},
  artifacts:[{
    id:"fixture-gguf",
    role:"original",
    format:"gguf",
    filename:"fixture.gguf",
    sha256:$hash,
    validation:{status:"unverified"}
  }]
}' > "$TMP/valid.manifest.json"

bash "$CLI" version >/dev/null
bash "$CLI" status >/dev/null
pass "version and status commands"

bash "$CLI" register "$TMP/valid.manifest.json" >/dev/null
bash "$CLI" list | grep -q 'tests/fixture-model'
bash "$CLI" inspect tests/fixture-model >/dev/null
pass "register, list, and inspect"

expect_fail "duplicate model registration is rejected" bash "$CLI" register "$TMP/valid.manifest.json"
expect_fail "missing artifact fails verification" bash "$CLI" verify tests/fixture-model

# A malformed JSON document and a schema-invalid document must not be accepted.
printf '{broken json\n' > "$TMP/broken.json"
expect_fail "malformed JSON is rejected" bash "$CLI" register "$TMP/broken.json"
jq -n '{manifest_version:"1.0",id:"tests/invalid",version:"1",publisher:"x"}' > "$TMP/invalid.json"
expect_fail "schema-invalid manifest is rejected" bash "$CLI" register "$TMP/invalid.json"

# Path traversal IDs and filenames must be rejected before any write/download.
jq --arg hash "$HASH" '.id="../escape"' "$TMP/valid.manifest.json" > "$TMP/traversal-id.json"
expect_fail "traversal model id is rejected" bash "$CLI" register "$TMP/traversal-id.json"
expect_fail "unsafe download filename is rejected" bash "$CLI" pull https://example.invalid/model.gguf --filename ../escape.gguf
expect_fail "malformed expected digest is rejected" bash "$CLI" pull https://example.invalid/model.gguf --sha256 nope

# Exercise a successful download, content-addressed storage, and verification.
export TEST_DOWNLOAD_SOURCE="$TMP/payload.gguf"
PATH="$FAKE_BIN:$PATH" bash "$CLI" pull https://example.invalid/model.gguf --sha256 "$HASH" --filename fixture.gguf >/dev/null
bash "$CLI" verify tests/fixture-model >/dev/null
pass "HTTPS pull, hash verification, content-addressed storage, and manifest status"

# A mismatched expected digest must fail and quarantine the downloaded bytes.
expect_fail "download hash mismatch is rejected" env PATH="$FAKE_BIN:$PATH" TEST_DOWNLOAD_SOURCE="$TMP/payload.gguf" \
  bash "$CLI" pull https://example.invalid/bad.gguf --sha256 "0000000000000000000000000000000000000000000000000000000000000000" --filename bad.gguf
find "$REGISTRY/quarantine" -type f -name 'bad.gguf.*' | grep -q .
pass "mismatched download is quarantined"

# Verify fails closed when jq is unavailable. Keep only the two commands needed
# before the dependency check on PATH.
mkdir -p "$TMP/no-jq"
for tool in dirname mkdir; do
  command -v "$tool" >/dev/null 2>&1 && ln -s "$(command -v "$tool")" "$TMP/no-jq/$tool"
done
expect_fail "verification fails closed without jq" env PATH="$TMP/no-jq" \
  LLM_MODELS_REGISTRY="$REGISTRY" /bin/bash bash "$CLI" verify tests/fixture-model

printf '\nAll LLM-models regression tests passed.\n'
