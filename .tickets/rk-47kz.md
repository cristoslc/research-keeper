---
id: rk-47kz
status: closed
deps: [rk-ehyq]
links: []
created: 2026-04-07T20:18:42Z
type: task
priority: 2
assignee: cristos
parent: rk-ss1i
tags: [spec:SPEC-052]
---
# Add model-tier detection and adaptive prompting

Detect lower-weight models via model name pattern (gemma*, phi*), invoke discovery loop only for those tiers.


## Notes

**2026-04-07T20:38:56Z**

Created detect-model-tier.sh: identifies lower-weight models (gemma*, phi*) vs higher-tier (claude*, gpt*, o1*). Returns LOWER_WEIGHT (exit 1), HIGHER_TIER (exit 0), or UNKNOWN (exit 2). Updated SKILL.md to invoke discovery loop for lower-weight/unknown models, standard workflow for higher-tier.
