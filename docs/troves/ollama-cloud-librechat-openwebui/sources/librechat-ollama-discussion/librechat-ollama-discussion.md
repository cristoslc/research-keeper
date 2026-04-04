---
title: "Running Ollama Locally - LibreChat GitHub Discussion #3722"
source-type: forum
url: "https://github.com/danny-avila/LibreChat/discussions/3722"
fetched: 2026-04-03
---

# LibreChat + Ollama Connection Issues (GitHub Discussion #3722)

## Scenario

Users exploring connecting LibreChat (running on a remote server) to Ollama (running on a local PC with GPU). The goal: run LibreChat on a data center server without GPU and send requests to a local machine with an RTX 4090 Ti.

## Common Issues

### Base URL Configuration

Multiple base URL variants attempted, most don't work:

- `http://127.0.0.1:11434/v1/chat/completions` — wrong (too specific)
- `http://host.docker.internal:11434/v1/chat/completions` — wrong path
- `http://localhost:11434/v1/` — only works if not in Docker
- `http://host.docker.internal:11434/v1/` — correct for Docker-to-host

### Key Insight

If running Ollama separately from LibreChat (not in the same Docker Compose), you must expose the Ollama API Server. The working config:

```yaml
- name: "Ollama"
  apiKey: "ollama"
  baseURL: "http://host.docker.internal:11434/v1/"
  models:
    default: ["llama3:latest"]
    fetch: true
  titleConvo: true
  titleModel: "current_model"
```

### Cross-Tool Comparison

The same user reports Ollama works with Open WebUI and Obsidian but not LibreChat — suggesting the issue is LibreChat-specific URL handling, not Ollama exposure.

## Remote Server to Local GPU

For remote LibreChat connecting to local Ollama:

1. Set `OLLAMA_HOST=0.0.0.0` on the Ollama machine
2. Open port 11434 on the local machine's firewall
3. Use the public IP or VPN tunnel in LibreChat's base URL
4. Consider security: Ollama has no built-in authentication
