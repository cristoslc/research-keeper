---
title: "Running AI Models Locally with Remote Access: Ollama, Open WebUI, and Cloudflare Setup"
source-type: web
url: "https://dasroot.net/posts/2025/12/running-ai-models-locally-remote-access-ollama-open-webui-cloudflare/"
fetched: 2026-04-03
---

# Ollama + Open WebUI + Cloudflare Tunnel for Remote Access

## Hardware Requirements

- **GPU**: NVIDIA RTX 30/40 series or A100. RTX 4090 (24GB vRAM) handles up to 27B params; A100 (80GB) for larger models.
- **RAM**: 64GB minimum for 70B models, 128GB+ ideal
- **Storage**: NVMe SSDs, 500GB+ for model storage
- **Software**: Docker 25.0+, CUDA 12.1+, NVIDIA drivers 535.181.05+

## Performance Benchmarks

| Model | GPU | RAM (GB) | Tokens/sec | Latency (ms) |
|---|---|---|---|---|
| Llama3:70B | A100 (80GB) | 128 | 250 | 12 |
| Gemma:27B | RTX 4090 | 64 | 180 | 18 |
| Phi4:13B | RTX 3090 | 32 | 110 | 30 |

## Docker Compose Configuration

```yaml
version: '3.8'
services:
  webui:
    image: ghcr.io/open-webui/open-webui:main
    ports:
      - "8080:8080"
    environment:
      - OLLAMA_BASE_URL=http://host.docker.internal:11434
    volumes:
      - open-webui:/app/backend/data
    depends_on:
      - ollama

  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama:/root/.ollama
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              device_ids: ['all']
              capabilities: [gpu]

  tunnel:
    image: cloudflare/cloudflared:latest
    restart: unless-stopped
    environment:
      - TUNNEL_URL=http://webui:8080
    command: tunnel --no-autoupdate
    depends_on:
      - webui

volumes:
  ollama:
  open-webui:
```

## Cloudflare Tunnel Security

- **Encryption**: TLS 1.3 for all traffic
- **Firewall protection**: Cloudflare's network shields internal infrastructure
- **DDoS mitigation**: Automatic malicious traffic filtering
- **Zero Trust**: Only authorized users access the service

Retrieve the tunnel URL with:

```bash
docker compose logs tunnel
```

The URL format is `https://<random-string>.trycloudflare.com`.

## Optimization Tips

- Use model quantization (Q2_K, Q3_K) to reduce memory usage
- Enable GPU offloading with `OLLAMA_CUDA=1`
- Use persistent volumes to avoid I/O bottlenecks
