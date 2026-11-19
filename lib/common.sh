#!/usr/bin/env bash
# LLM-models common library
# Shared helpers for the local registry CLI.

set -euo pipefail

if [[ -n "\${LLM_MODELS_ROOT:-}" ]]; then
  ROOT="$LLM_MODELS_ROOT"
else
  ROOT="$(cd "$(dirname "\${BASH_SOURCE[0]}")/.." && pwd)"
fi

REGISTRY_DIR="\${LLM_MODELS_REGISTRY:-$ROOT/registry}"
MANIFESTS_DIR="$REGISTRY_DIR/manifests"
ARTIFACTS_DIR="$REGISTRY_DIR/artifacts"
DOWNLOADS_DIR="$REGISTRY_DIR/downloads"
QUARANTINE_DIR="$REGISTRY_DIR/quarantine"
LOGS_DIR="$REGISTRY_DIR/logs"
SCHEMA_FILE="$ROOT/schemas/model-manifest.schema.json"

log()  { printf '[llm-models] %s\n' "$*" >&2; }
ok()   { printf '[✓] %s\n' "$*" >&2; }
warn() { printf '[!] %s\n' "$*" >&2; }
err()  { printf '[✗] %s\n' "$*" >&2; }
die()  { err "$*"; exit 1; }

require_command() {
  local command_name="$1"
  command -v "$command_name" >/dev/null 2>&1 ||
    die "Required command not found: $command_name"
}

require_json_tools() {
  require_command jq
  require_command check-jsonschema
  [[ -r "$SCHEMA_FILE" ]] || die "Manifest schema is missing or unreadable: $SCHEMA_FILE"
}

ensure_registry() {
  mkdir -p "$MANIFESTS_DIR" "$ARTIFACTS_DIR" "$DOWNLOADS_DIR" \
    "$QUARANTINE_DIR" "$LOGS_DIR"
  if [[ ! -f "$REGISTRY_DIR/README.md" ]]; then
    cat > "$REGISTRY_DIR/README.md" <<'EOF'
# Local Registry Store

This directory is the local model registry.

- manifests/   — registered model manifests (JSON)
- artifacts/  — content-addressed artifacts, keyed by SHA-256
- downloads/  — resumable partial downloads
- quarantine/ — artifacts that failed integrity checks
- logs/       — operation history

Use the CLI to manage registry contents.
EOF
  fi
}

validate_model_id() {
  local id="$1"
  [[ "$id" =~ ^[A-Za-z0-9][A-Za-z0-9._/-]*$ ]] ||
    die "Invalid model id '$id': use letters, digits, '.', '_', '-', and '/'"
  [[ "$id" != *".."* && "$id" != */ && "$id" != *//* ]] ||
    die "Invalid model id '$id': empty or traversal path segments are not allowed"
}

validate_filename() {
  local filename="$1"
  [[ "$filename" =~ ^[A-Za-z0-9][A-Za-z0-9._+-]*$ ]] ||
    die "Unsafe filename '$filename': use a simple filename without path separators"
  [[ "$filename" != "." && "$filename" != ".." ]] ||
    die "Unsafe filename '$filename'"
}

manifest_path() {
  local id="$1"
  validate_model_id "$id"
  local safe
  safe="\${id//\//__}"
  printf '%s/%s.manifest.json\n' "$MANIFESTS_DIR" "$safe"
}

list_manifests() {
  ensure_registry
  find "$MANIFESTS_DIR" -maxdepth 1 -type f -name '*.manifest.json' -print 2>/dev/null | sort
}

json_get() {
  local file="$1"
  local key="$2"
  require_command jq
  jq -er --arg k "$key" '.[$k] | select(. != null) | if type == "string" then . else tostring end' "$file"
}

validate_manifest() {
  local file="$1"
  require_json_tools
  jq -e 'type == "object"' "$file" >/dev/null ||
    die "Manifest is not a valid JSON object: $file"
  check-jsonschema --schemafile "$SCHEMA_FILE" "$file" ||
    die "Manifest does not conform to the repository JSON Schema: $file"
  jq -e '[.artifacts[].id] as $ids | ($ids | length) == ($ids | unique | length)' "$file" >/dev/null ||
    die "Manifest contains duplicate artifact IDs"
  local id
  id=$(jq -er '.id | strings | select(length > 0)' "$file") ||
    die "Manifest has no valid model id"
  validate_model_id "$id"
}

validate_sha256() {
  local hash="$1"
  [[ "$hash" =~ ^[A-Fa-f0-9]{64}$ ]] ||
    die "Invalid SHA-256 digest: expected exactly 64 hexadecimal characters"
}

sha256_file() {
  local file="$1"
  [[ -f "$file" ]] || die "File not found for SHA-256: $file"
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum -- "$file" | awk '{print $1}'
  elif command -v shasum >/dev/null 2>&1; then
    shasum -a 256 -- "$file" | awk '{print $1}'
  else
    die "No SHA-256 tool found (need sha256sum or shasum)"
  fi
}

artifact_store_path() {
  local hash="$1"
  validate_sha256 "$hash"
  hash="$(printf '%s' "$hash" | tr '[:upper:]' '[:lower:]')"
  printf '%s/%s/%s\n' "$ARTIFACTS_DIR" "\${hash:0:2}" "$hash"
}

store_artifact() {
  local src="$1"
  local expected_hash="\${2:-}"
  [[ -f "$src" ]] || die "Artifact file not found: $src"

  if [[ -n "$expected_hash" ]]; then
    validate_sha256 "$expected_hash"
    expected_hash="$(printf '%s' "$expected_hash" | tr '[:upper:]' '[:lower:]')"
  fi

  local actual dest dest_dir tmp
  actual=$(sha256_file "$src")
  if [[ -n "$expected_hash" && "$actual" != "$expected_hash" ]]; then
    die "Hash mismatch for $src (expected $expected_hash, got $actual)"
  fi

  dest=$(artifact_store_path "$actual")
  dest_dir="$(dirname "$dest")"
  mkdir -p "$dest_dir"

  if [[ -e "$dest" ]]; then
    [[ -f "$dest" ]] || die "Artifact store path exists but is not a regular file: $dest"
    [[ "$(sha256_file "$dest")" == "$actual" ]] ||
      die "Existing content-addressed object is corrupt: $dest"
  else
    tmp=$(mktemp "$dest_dir/.artifact.XXXXXX")
    if ! cp -- "$src" "$tmp"; then
      rm -f -- "$tmp"
      die "Could not copy artifact into the registry store"
    fi
    chmod 0444 "$tmp" 2>/dev/null || true
    if ! ln -- "$tmp" "$dest"; then
      rm -f -- "$tmp"
      [[ -f "$dest" && "$(sha256_file "$dest")" == "$actual" ]] ||
        die "Could not publish artifact into the registry store"
    else
      rm -f -- "$tmp"
    fi
  fi

  printf '%s\n' "$actual"
}

audit_log() {
  ensure_registry
  local timestamp
  timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  printf '%s %s\n' "$timestamp" "$*" >> "$LOGS_DIR/operations.log"
}
