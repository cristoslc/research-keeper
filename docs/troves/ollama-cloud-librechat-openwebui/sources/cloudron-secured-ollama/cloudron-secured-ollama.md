---
title: "How to configure LibreChat to discuss with secured self-hosted Ollama?"
source-type: forum
url: "https://forum.cloudron.io/topic/14484/how-to-configure-librechat-to-discuss-with-secured-self-hosted-ollama"
fetched: 2026-04-03
---

# LibreChat + Secured Self-Hosted Ollama on Cloudron

## Problem

User installed LibreChat and Ollama on Cloudron. LibreChat works with Mistral (via API key) but cannot connect to the self-hosted Ollama instance.

## Root Cause

LibreChat has legacy code where headers are not expected when the endpoint name is "ollama". This is tracked in GitHub issue danny-avila/LibreChat#10311.

## Workaround

Change the custom endpoint name from "ollama" to something else (e.g., "CloudronOllama"):

```yaml
version: 1.2.8
endpoints:
  custom:
    - name: "CloudronOllama"
      apiKey: "ollama"
      baseURL: "https://ollama-api.cloudron.dev/v1/"
      models:
        default: ["tinyllama:latest"]
        fetch: true
      titleConvo: true
      titleModel: "current_model"
```

## Key Takeaway

When Ollama is behind a reverse proxy that adds authentication headers, LibreChat's handling of the "ollama" endpoint name causes issues. The fix is to use a different name for the custom endpoint. Ollama itself accepts headers fine — the problem is on the LibreChat side.

## Security Note

Hosted Ollama instances (like on Cloudron) typically sit behind a reverse proxy with auth. The documentation is sparse about this scenario — most guides assume localhost access without authentication.
