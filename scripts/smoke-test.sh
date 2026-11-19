#!/usr/bin/env bash
# Basic smoke test for the M1/M2 foundation
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CLI="$ROOT/cli/llm-models"
EXAMPLE="$ROOT/examples/phi-3.5-mini.example.manifest.json"

echo "== version =="
bash "$CLI" version

echo ""
echo "== status =="
bash "$CLI" status

echo ""
echo "== register example manifest =="
bash "$CLI" register "$EXAMPLE"

echo ""
echo "== list =="
bash "$CLI" list

echo ""
echo "== inspect =="
bash "$CLI" inspect "example/phi-3.5-mini"

echo ""
echo "== verify (expected to fail on placeholder hash) =="
set +e
bash "$CLI" verify "example/phi-3.5-mini"
rc=$?
set -e
echo "verify exit code: $rc (non-zero is expected for the example zero-hash)"

echo ""
echo "Smoke test finished."