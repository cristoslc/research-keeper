---
title: "Custom Endpoints - LibreChat"
source-type: web
url: "https://www.librechat.ai/docs/quick_start/custom_endpoints"
fetched: 2026-04-03
---

# LibreChat Custom Endpoints

LibreChat supports any OpenAI API-compatible service as a custom endpoint. Configuration uses three files:

1. **`librechat.yaml`** — defines custom endpoints (name, API URL, models, display settings)
2. **`.env`** — stores API keys (referenced via `${VAR_NAME}` syntax)
3. **`docker-compose.override.yml`** — mounts librechat.yaml into the Docker container

## Docker Volume Mount

```yaml
services:
  api:
    volumes:
      - type: bind
        source: ./librechat.yaml
        target: /app/librechat.yaml
```

## Example Configuration with Ollama

```yaml
version: 1.3.5
cache: true
endpoints:
  custom:
    - name: "OpenRouter"
      apiKey: "${OPENROUTER_KEY}"
      baseURL: "https://openrouter.ai/api/v1"
      models:
        default: ["meta-llama/llama-3-70b-instruct"]
        fetch: true
      titleConvo: true
      titleModel: "meta-llama/llama-3-70b-instruct"
      dropParams: ["stop"]
      modelDisplayLabel: "OpenRouter"
    - name: "Ollama"
      apiKey: "ollama"
      baseURL: "http://host.docker.internal:11434/v1/"
      models:
        default: ["llama3:latest", "command-r", "mixtral", "phi3"]
        fetch: true
      titleConvo: true
      titleModel: "current_model"
```

## API Key Options

1. **Environment variable** (recommended): `apiKey: "${OPENROUTER_KEY}"`
2. **User provided**: `apiKey: "user_provided"` — users enter their own key in the UI
3. **Direct value** (not recommended): `apiKey: "sk-your-actual-key"`

## Key Details

- Ollama uses `"ollama"` as a dummy API key
- Base URL for Docker: `http://host.docker.internal:11434/v1/`
- `fetch: true` lets LibreChat auto-discover available models
- Restart required after config changes: `docker compose down && docker compose up -d`
