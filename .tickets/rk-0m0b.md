---
id: rk-0m0b
status: closed
deps: [rk-kztd]
links: []
created: 2026-04-07T20:18:38Z
type: task
priority: 2
assignee: cristos
parent: rk-ss1i
tags: [spec:SPEC-052]
---
# Implement subagent prompt templates with step confirmation

Create prompt templates that force sequential execution with explicit confirmations ('Reply STEP 1 COMPLETE before continuing').


## Notes

**2026-04-07T20:38:01Z**

Created subagent prompt templates reference: base template (iteration 1), refined template (iterations 2-4 with missing steps injected), critical template (iteration 5+ with error reporting). Includes explicit 'STEP N COMPLETE' confirmation requirements, error reporting format, and model-specific adaptations for gemma4/phi.
