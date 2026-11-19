# StackAlign Integration Notes (M6 target)

This document describes the **intended narrow contract** between StackAlign and LLM-models.  
It is not yet implemented.

## Principle

StackAlign owns the host and infrastructure.  
LLM-models owns the models.  

StackAlign must not grow mandatory Python, PyTorch, or model-download dependencies in its core path.

## Service Contract (proposed)

A running model service managed by LLM-models should expose (at least):

```json
{
  "service": "llm-models",
  "model_id": "publisher/name",
  "version": "1.2.3",
  "endpoint": "http://127.0.0.1:8080",
  "health": "ok | degraded | down",
  "backend": "llama.cpp | onnxruntime | other",
  "resource_requirements": {
    "ram_mb": 8192,
    "gpu": "optional"
  },
  "deployed_at": "2026-11-18T00:00:00Z"
}
```

## Responsibilities

| Concern | Owner |
|---------|-------|
| Host provisioning, packages, firewall | StackAlign |
| Model discovery, pull, verify, prepare | LLM-models |
| Inference process lifecycle | LLM-models |
| Whether the service is healthy | LLM-models (reports) |
| Whether the host allows the port / process | StackAlign |

## What StackAlign should *not* do

- Embed GGUF/ONNX download logic
- Perform quantization
- Start model servers as part of core `install`
- Assume any particular model is present

## Discovery options (future)

1. Well-known local file written by LLM-models (e.g. `/var/lib/llm-models/current.json`)
2. Optional systemd unit / socket activation coordinated by the operator
3. Explicit operator configuration in StackAlign pointing at the endpoint

All of the above remain optional. Core StackAlign continues to function without LLM-models.