#!/usr/bin/env bash
# LLM-models common library
# Shared helpers for the local registry CLI

set -euo pipefail

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

# Resolve repository root from this file's location when possible
if [[ -n "${LLM_MODELS_ROOT:-}" ]]; then
  ROOT="$LLM_MODELS_ROOT"
elif [[ -n "${BASH_SOURCE[0]:-}" ]]; then
  ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
else
  ROOT="$(pwd)"
fi

REGISTRY_DIR="${LLM_MODELS_REGISTRY:-$ROOT/registry}"
MANIFESTS_DIR="$REGISTRY_DIR/manifests"
ARTIFACTS_DIR="$REGISTRY_DIR/artifacts"
QUARANTINE_DIR="$REGISTRY_DIR/quarantine"
LOGS_DIR="$REGISTRY_DIR/logs"
SCHEMA_FILE="$ROOT/schemas/model-manifest.schema.json"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

log()  { printf '[llm-models] %s\n' "$*"; }
ok()   { printf '[✓] %s\n' "$*"; }
warn() { printf '[!] %s\n' "$*" >&2; }
err()  { printf '[✗] %s\n' "$*" >&2; }
die()  { err "$*"; exit 1; }

# ---------------------------------------------------------------------------
# Registry bootstrap
# ---------------------------------------------------------------------------

ensure_registry() {
  mkdir -p "$MANIFESTS_DIR" "$ARTIFACTS_DIR" "$QUARANTINE_DIR" "$LOGS_DIR"
  if [[ ! -f "$REGISTRY_DIR/README.md" ]]; then
    cat > "$REGISTRY_DIR/README.md" <<'EOF'
# Local Registry Store

This directory is the content-addressed local registry.

- manifests/   — registered model manifests (JSON)
- artifacts/   — verified artifact files (content-addressed by SHA-256)
- quarantine/  — artifacts or manifests that failed validation
- logs/        — operation history

Do not manually edit verified artifacts. Use the CLI.
EOF
  fi
}

# ---------------------------------------------------------------------------
# Hash helpers
# ---------------------------------------------------------------------------

sha256_file() {
  local f="$1"
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$f" | awk '{print $1}'
  elif command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$f" | awk '{print $1}'
  else
    die "No SHA-256 tool found (need sha256sum or shasum)"
  fi
}

# ---------------------------------------------------------------------------
# Manifest helpers
# ---------------------------------------------------------------------------

manifest_path() {
  local id="$1"
  # Sanitize id for filesystem
  local safe
  safe=$(echo "$id" | tr '/:' '__')
  echo "$MANIFESTS_DIR/${safe}.manifest.json"
}

list_manifests() {
  ensure_registry
  find "$MANIFESTS_DIR" -maxdepth 1 -name '*.manifest.json' -type f 2>/dev/null | sort
}

# Very light JSON field extraction without requiring jq (fallback)
json_get() {
  local file="$1"
  local key="$2"
  if command -v jq >/dev/null 2>&1; then
    jq -r --arg k "$key" '.[$k] // empty' "$file" 2>/dev/null || true
  else
    # crude grep/sed fallback for simple top-level string fields
    grep -o "\"$key\"[[:space:]]*:[[:space:]]*\"[^\"]*\"" "$file" 2>/dev/null \
      | head -1 \
      | sed -E 's/.*:[[:space:]]*"([^"]*)".*/\1/' || true
  fi
}

# ---------------------------------------------------------------------------
# Artifact content-addressed storage
# ---------------------------------------------------------------------------

artifact_store_path() {
  local hash="$1"
  local prefix="${hash:0:2}"
  echo "$ARTIFACTS_DIR/$prefix/$hash"
}

store_artifact() {
  local src="$1"
  local expected_hash="${2:-}"

  [[ -f "$src" ]] || die "Artifact file not found: $src"

  local actual
  actual=$(sha256_file "$src")

  if [[ -n "$expected_hash" && "$actual" != "$expected_hash" ]]; then
    die "Hash mismatch for $src
  expected: $expected_hash
  actual:   $actual"
  fi

  local dest
  dest=$(artifact_store_path "$actual")
  mkdir -p "$(dirname "$dest")"

  if [[ -f "$dest" ]]; then
    log "Artifact already present: $actual"
  else
    cp -n "$src" "$dest"
    ok "Stored artifact $actual"
  fi

  echo "$actual"
}

# ---------------------------------------------------------------------------
# Validation status helpers
# ---------------------------------------------------------------------------

is_verified_status() {
  local status="$1"
  [[ "$status" == "verified" ]]
}

# ---------------------------------------------------------------------------
# Logging operations
# ---------------------------------------------------------------------------

audit_log() {
  ensure_registry
  local ts
  ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  echo "$ts $*" >> "$LOGS_DIR/operations.log"
}