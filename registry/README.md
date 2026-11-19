# Local Registry Store

This directory is the content-addressed local registry.

- manifests/   — registered model manifests (JSON)
- artifacts/   — verified artifact files (content-addressed by SHA-256)
- quarantine/  — artifacts or manifests that failed validation
- logs/        — operation history

Do not manually edit verified artifacts. Use the CLI.
