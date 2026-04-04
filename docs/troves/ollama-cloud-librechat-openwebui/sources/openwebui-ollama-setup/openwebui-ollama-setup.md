---
title: "Ollama - Open WebUI"
source-type: web
url: "https://docs.openwebui.com/getting-started/quick-start/connect-a-provider/starting-with-ollama/"
fetched: 2026-04-03
---

# Open WebUI + Ollama Setup

## Protocol-Oriented Design

Open WebUI is **protocol-oriented** — when it refers to "Ollama", it means the Ollama API Protocol (port 11434). This connection type is optimized for Ollama-specific features like native model management and pulling models through the Admin UI.

If your backend is OpenAI-compatible (like LocalAI or Docker Model Runner), use the OpenAI-Compatible Server guide instead.

## Connection Setup

Once installed, Open WebUI automatically attempts to connect to your Ollama instance. Most connection issues stem from network misconfiguration.

## Managing Ollama

1. Go to **Admin Settings**
2. Navigate to **Connections > Ollama > Manage** (wrench icon)
3. Download models, configure settings, manage connection

### Connection Tips

- **Docker users**: Use `http://host.docker.internal:11434` as the URL
- **Load balancing**: Add multiple Ollama instances — Open WebUI distributes requests via random selection. Model IDs must match exactly across instances.

### Advanced Configuration

- **Prefix ID**: Use a prefix (e.g., `remote/`) to distinguish multiple instances serving the same models
- **Model IDs (Filter)**: Whitelist specific models; leave empty to show all

### Connection Timeout

```
AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST=3
```

Lower the timeout (default 10s) for faster failover when using multiple instances.

## Quick Model Download

Type a model name in the Model Selector — if not available, Open WebUI prompts you to download it from Ollama.

## Reasoning / Thinking Models

For models like DeepSeek-R1 or Qwen3 that use `<think>...</think>` tags:

```
ollama serve --reasoning-parser deepseek_r1
```

This separates thinking blocks from final answers in the UI.
