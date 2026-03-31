# Agent Sandboxing Methods: Synthesis

Trove: `agent-sandboxing-methods`
Created: 2026-03-15 | Imported: 2026-03-30

## Context

Research into sandboxing methods for running Claude Code headlessly in isolated environments, targeting three platforms: macOS (Apple Silicon), Linux desktop, and Linux headless server. Primary use case: a polling daemon that processes GitHub issues via Claude Code without operator interaction.

---

## Method Comparison Table

| Method | Isolation Level | macOS (Apple Silicon) | Linux Desktop | Linux Server (headless) | Claude Code Support | Headless/Non-interactive | Network Control | License / Cost |
|---|---|---|---|---|---|---|---|---|
| **Claude Code built-in sandbox** (seatbelt + bubblewrap) | OS-level process sandbox | Yes (seatbelt) | Yes (bubblewrap) | Yes (bubblewrap) | Native | Yes | Domain allowlist via proxy | Free, open-source (sandbox-runtime npm pkg) |
| **Docker Sandboxes** (`docker sandbox run`) | microVM (macOS/Win) or container (Linux) | Yes (microVM) | Yes (legacy container) | No -- requires Docker Desktop | First-class (built-in agent) | Yes | Network namespace isolation | Requires Docker Desktop (free <250 employees + <$10M rev) |
| **Plain Docker containers** (`docker run`) | Container (shared kernel) | Yes (via Docker Desktop or Colima) | Yes | Yes (docker-ce) | Community images exist | Yes | `--network none` or custom | docker-ce: free; Docker Desktop: conditional |
| **Bubblewrap (bwrap)** | OS-level namespace sandbox | No (Linux only) | Yes | Yes | Used by Claude Code internally | Yes | `--unshare-net` | Free, open-source (LGPL) |
| **macOS Seatbelt (sandbox-exec)** | OS-level process sandbox | Yes | No | No | Used by Claude Code internally | Yes | Via proxy outside sandbox | Free (macOS built-in, but deprecated API) |
| **Apple Containerization** | VM-per-container (Virtualization.framework) | Yes (macOS 26+, Apple Silicon) | No | No | Not yet -- too new | Yes | VM-level isolation | Free, open-source (Apache 2.0) |
| **Firecracker microVMs** | Full microVM (own kernel) | No (Linux+KVM only) | Yes (with KVM) | Yes (with KVM) | Via custom setup | Yes | VM-level network namespace | Free, open-source (Apache 2.0) |
| **gVisor (runsc)** | User-space kernel | No (Linux only) | Yes | Yes | Via K8s Agent Sandbox | Yes | Network policy enforcement | Free, open-source (Apache 2.0) |
| **Kata Containers** | Lightweight VM | No (Linux only) | Yes (with KVM) | Yes (with KVM) | Via K8s Agent Sandbox | Yes | VM-level isolation | Free, open-source (Apache 2.0) |
| **LXC/Incus (LXD fork)** | System container or VM | Client only (daemon Linux-only) | Yes | Yes | Manual setup | Yes | Network namespaces, firewall rules | Free, open-source (Apache 2.0) |
| **nsjail** | Namespace + seccomp sandbox | No (Linux only) | Yes | Yes | Manual setup | Yes | Network namespace isolation | Free, open-source (Apache 2.0) |
| **E2B** | Firecracker microVM (cloud) | Yes (cloud API) | Yes (cloud API) | Yes (cloud API) | First-class template | Yes | Cloud-side isolation | Free tier ($100 credit), Pro $150/mo, self-host possible |

---

## Platform Groupings

### Works Everywhere (macOS + Linux Desktop + Linux Server)

**1. Claude Code built-in sandbox (sandbox-runtime)**
- The path of least resistance. Uses seatbelt on macOS and bubblewrap on Linux automatically.
- Filesystem isolation: writes restricted to CWD. Network isolation: domain allowlist via proxy.
- Open-source npm package (`@anthropic-ai/sandbox-runtime`) usable in custom agent harnesses.
- Limitation: process-level isolation only, not a full VM or container boundary. A kernel exploit could escape.
- Limitation: sandbox-exec on macOS is a deprecated Apple API. Still works, but long-term uncertain.

**2. Plain Docker containers**
- On macOS: requires Docker Desktop, Colima, or OrbStack to provide the Linux VM layer.
- On Linux desktop/server: works with free docker-ce, no Docker Desktop needed.
- Run Claude Code with `--dangerously-skip-permissions -p "prompt"` inside a container with `--network none`.
- Anthropic provides a reference devcontainer setup with firewall rules.
- Community images: `tintinweb/claude-code-container`, `textcortex/claude-code-sandbox`.
- Isolation is container-level (shared kernel), not VM-level.
- **Best option for headless Linux servers** that need to avoid Docker Desktop.

**3. E2B (cloud API)**
- Works from any platform since it is a cloud service accessed via API.
- Firecracker microVMs provide strong isolation. 150ms cold start.
- Has an official Claude Code template with headless `--dangerously-skip-permissions -p` support.
- Trade-off: external dependency, ongoing cost ($0.05/hr per sandbox), 24-hour session limit.
- Self-hosting possible (Apache 2.0) but operationally complex (Terraform + Nomad).

### macOS Only

**4. macOS Seatbelt (sandbox-exec)**
- Built into macOS. No installation needed.
- Used by Claude Code's built-in sandbox automatically.
- Can be used standalone via `sandbox-exec` with custom .sb profiles.
- Apple marks it as deprecated -- functional today but uncertain future.
- Community tools: `agent-seatbelt-sandbox` for data egress prevention.

**5. Apple Containerization (new)**
- VM-per-container architecture via Virtualization.framework.
- Requires macOS 26 (Tahoe) and Apple Silicon. OCI-compatible images.
- Very new (WWDC 2025). No Claude Code integration yet.
- Potential Docker Desktop replacement for macOS development.
- Worth watching but not production-ready for this use case today.

### Linux Only

**6. Bubblewrap (bwrap)**
- Used by Claude Code internally on Linux. Lightweight, zero overhead.
- Namespace-based: filesystem, PID, network, user isolation.
- Network blocked via `--unshare-net`; selective access via socat proxy forwarding.
- Available via system package managers (apt, dnf).
- Not available on macOS (requires Linux kernel namespaces).

**7. Firecracker microVMs**
- Strongest isolation: each workload gets its own kernel. 125ms boot, <5MiB overhead.
- Requires Linux host with KVM support. Does not run on macOS.
- Apache 2.0 license. Used by E2B, AWS Lambda, Fly.io under the hood.
- Requires custom integration to run Claude Code inside a microVM.
- BunkerVM project provides a REST API wrapper for Firecracker agent sandboxing.
- Best for high-security headless Linux servers where container isolation is insufficient.

**8. gVisor (runsc)**
- User-space kernel that intercepts syscalls. Stronger than containers, lighter than VMs.
- Drop-in OCI runtime: `docker run --runtime=runsc`.
- Linux only. Supports x86_64 and ARM64.
- Kubernetes Agent Sandbox (k8s-sigs) provides native gVisor integration for AI agents.
- Good middle ground between Docker containers and Firecracker for Linux servers.

**9. Kata Containers**
- Lightweight VMs that behave like containers. OCI-compatible runtime.
- Requires Linux with KVM. Hardware virtualization mandatory.
- Integrated with Kubernetes Agent Sandbox for AI workloads.
- Heavier startup than gVisor but stronger isolation (real VM boundary).
- Good for Kubernetes-based deployments on Linux servers.

**10. nsjail**
- Google's process isolation tool. Namespaces + cgroups + seccomp-bpf.
- Very lightweight, configuration-file driven.
- Linux only. No macOS support.
- Less community adoption for AI agents compared to bubblewrap or gVisor.
- Useful if you need fine-grained syscall filtering beyond what bubblewrap provides.

**11. LXC/Incus**
- Full system containers (feel like a VM, run like a container).
- Incus daemon is Linux only. macOS can run the client to manage remote instances.
- Supports both containers and VMs via same interface.
- Good for persistent development environments on Linux servers.
- More operational overhead than Docker for ephemeral sandbox use.

### Requires Docker Desktop

**12. Docker Sandboxes (`docker sandbox run`)**
- microVM-based on macOS/Windows; legacy container-based on Linux.
- Requires Docker Desktop on all platforms. Does not work with standalone docker-ce.
- First-class Claude Code support: `docker sandbox run claude ~/project`.
- Each sandbox gets a private Docker daemon -- can even run Docker-in-Docker safely.
- Best UX of any option but the Docker Desktop requirement makes it unusable on headless Linux servers without a license.

---

## Recommendations by Deployment Scenario

### Scenario A: macOS dev machine (interactive development)

**Primary:** Claude Code built-in sandbox (automatic, zero setup).
**Enhanced:** Docker Sandboxes for full microVM isolation when running untrusted code or needing Docker-in-Docker.
**Future:** Apple Containerization when it matures (macOS 26+).

### Scenario B: Linux desktop (interactive development)

**Primary:** Claude Code built-in sandbox (bubblewrap, automatic).
**Enhanced:** Plain Docker container with `--network none` for stronger isolation.
**Alternative:** gVisor (`--runtime=runsc`) for user-space kernel isolation without VM overhead.

### Scenario C: Headless Linux server (polling daemon, no Docker Desktop)

This is the most constrained scenario and the primary use case for research-keeper's agent runtime.

**Recommended stack (layered):**

1. **Plain Docker container** as the outer boundary (docker-ce, free, no Desktop needed):
   - Mount only the project directory
   - Use `--network` with a custom bridge that limits egress to GitHub API + Anthropic API
   - Run Claude Code with `--dangerously-skip-permissions -p "prompt" --output-format stream-json`
   - Use Anthropic's reference devcontainer as a starting point

2. **Bubblewrap inside the container** (Claude Code's built-in sandbox):
   - Note: requires `enableWeakerNestedSandbox` mode when running inside Docker without privileged namespaces
   - This weakens isolation but still provides filesystem write restriction

3. **Alternative to Docker: Firecracker** for maximum isolation:
   - Each task gets its own microVM with its own kernel
   - Requires KVM on the host
   - Higher operational complexity, but strongest security boundary
   - Consider BunkerVM for REST API management

4. **Alternative to Docker: gVisor (runsc)** for middle-ground isolation:
   - Install as an OCI runtime alongside docker-ce
   - `docker run --runtime=runsc` gives user-space kernel isolation
   - Lower overhead than Firecracker, stronger than plain containers

**For the polling daemon specifically:**
- Start with plain Docker containers + docker-ce. This is the simplest path that avoids Docker Desktop.
- Add gVisor (`--runtime=runsc`) if container-escape risk is a concern.
- Graduate to Firecracker if you need hard VM boundaries (e.g., processing untrusted repo content).
- Use E2B cloud as a managed alternative if you want to avoid infrastructure management entirely.

### Scenario D: CI/CD pipelines

**Primary:** Plain Docker containers with `--dangerously-skip-permissions -p` and `--output-format stream-json`.
**Enhanced:** gVisor runtime for stronger isolation in shared CI infrastructure.
**Managed:** E2B API for ephemeral sandboxes without managing infrastructure.

---

## Key Findings

1. **Docker Desktop is the blocker.** Docker Sandboxes (`docker sandbox run`) are the most polished option but require Docker Desktop, which has licensing implications and does not run on headless Linux servers. Plain docker-ce containers are the pragmatic workaround.

2. **Claude Code's built-in sandbox is the baseline.** It runs everywhere (macOS + Linux) and provides meaningful filesystem and network isolation at zero cost. However, it is process-level isolation, not a VM boundary.

3. **gVisor is the best Linux-only upgrade.** It slots in as a Docker runtime (`--runtime=runsc`) with minimal operational change, providing syscall interception without VM overhead.

4. **Firecracker is the gold standard for isolation** but requires KVM and custom integration. Best reserved for high-security environments or when E2B's managed offering is too expensive/constraining.

5. **Apple Containerization is worth watching** as a potential Docker Desktop replacement on macOS, but it is too new for production use today.

6. **sandbox-exec deprecation is a long-term risk** on macOS. Apple has deprecated the API but it still works. No replacement has been announced.

---

## Gaps

- No source coverage of Fly.io Machines as a sandboxing option (Firecracker-based, managed)
- Limited coverage of cost modeling for cloud-hosted sandbox options at scale
- No benchmarks comparing startup latency across methods under real agent workloads

## Sources

See `manifest.yaml` for the complete source list with URLs and fetch dates.
