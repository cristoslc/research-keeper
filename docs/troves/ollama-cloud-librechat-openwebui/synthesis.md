# Synthesis: Ollama Cloud with LibreChat and Open WebUI

## Three Deployment Patterns

The sources reveal three distinct ways to connect a chat UI to Ollama, each with different trade-offs.

### 1. Local Ollama + Local UI (simplest)

Both Ollama and the chat UI run on the same machine. Open WebUI auto-discovers Ollama at `localhost:11434` (openwebui-ollama-setup). LibreChat requires explicit configuration in `librechat.yaml` with `baseURL: "http://host.docker.internal:11434/v1/"` when both run in Docker (librechat-custom-endpoints). This pattern needs no network exposure but limits you to one machine's GPU.

### 2. Remote Ollama + Remote UI via Tunnel

Ollama and Open WebUI run on a GPU server, exposed to the internet through Cloudflare Tunnel. The tunnel provides TLS 1.3 encryption, DDoS mitigation, and zero-trust access without opening firewall ports (ollama-openwebui-cloudflare-remote). This is the recommended pattern for accessing your own GPU from anywhere. Docker Compose orchestrates all three services (Ollama, Open WebUI, Cloudflare Tunnel) in a single stack.

### 3. Ollama Cloud (no local GPU needed)

Ollama now offers cloud models that offload inference to Ollama's servers. You run `ollama signin`, then use cloud model tags like `gpt-oss:120b-cloud`. The API is also available directly at `https://ollama.com/api/chat` with Bearer auth (ollama-cloud-docs). This eliminates the GPU requirement entirely but sends data to Ollama's infrastructure.

## Open WebUI vs LibreChat for Ollama

**Open WebUI** has deeper Ollama integration (chat-uis-for-ollama):
- Native model management (pull/delete through the admin UI)
- Auto-discovery of Ollama instances
- Load balancing across multiple Ollama instances via random selection
- Protocol-oriented design specifically for the Ollama API

**LibreChat** treats Ollama as a generic OpenAI-compatible endpoint (librechat-custom-endpoints):
- Configured via `librechat.yaml` custom endpoints
- Uses `"ollama"` as a dummy API key
- Supports more provider types natively (OpenAI, Azure, Google, Anthropic)
- Has a known bug where naming the endpoint "ollama" breaks header handling (cloudron-secured-ollama)

## Common Pitfalls

### Network Configuration
- Ollama defaults to `127.0.0.1` — set `OLLAMA_HOST=0.0.0.0` for remote access (ollama-openwebui-cloudflare-remote)
- Docker users must use `host.docker.internal` not `localhost` (librechat-ollama-discussion)
- WSL users need port proxying from Windows to the WSL virtual network

### LibreChat-Specific Issues
- The base URL must end with `/v1/` — paths like `/v1/chat/completions` are wrong (librechat-ollama-discussion)
- Don't name the custom endpoint "ollama" if Ollama sits behind a reverse proxy with auth headers (cloudron-secured-ollama)
- Works with Open WebUI and Obsidian but not LibreChat? The issue is usually the URL format, not Ollama exposure

### Security
- Ollama has no built-in authentication — anyone with network access can manage the instance
- For remote access, use Cloudflare Tunnel or VPN rather than direct port forwarding
- Cloudron/reverse proxy setups need the LibreChat endpoint name workaround

## Gaps

- **Ollama Cloud pricing and limits** — the docs don't mention costs, rate limits, or data retention policies
- **Open WebUI + Ollama Cloud** — no source covers whether Open WebUI can connect to Ollama's cloud API directly (as a remote host)
- **LibreChat + Ollama Cloud** — unclear if LibreChat can use `https://ollama.com` as a base URL with Bearer auth
- **Multi-user auth** — both UIs support user accounts, but securing the Ollama backend itself for multi-tenant use is underdocumented
