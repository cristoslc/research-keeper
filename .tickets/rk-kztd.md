---
id: rk-kztd
status: closed
deps: [rk-x4tf, rk-jfzh]
links: []
created: 2026-04-07T20:18:37Z
type: task
priority: 2
assignee: cristos
parent: rk-ss1i
tags: [spec:SPEC-052]
---
# Implement discovery loop orchestrator script

Create discovery-loop.sh: manages iterations (max 5), tracks failures, dispatches subagents via ollama cloud, validates output, refines prompts.


## Notes

**2026-04-07T20:37:39Z**

Created discovery-loop.sh orchestrator: manages iterations (max 5), tracks failures, dispatches subagents via ollama cloud (simulated in mock), validates output after each iteration, refines prompts based on failure analysis. Generates failure report if convergence not achieved. Test run shows correct behavior: detects skipped steps, refines prompt with explicit step-by-step instructions, retries.
