---
id: rk-zo46
status: closed
deps: [rk-0m0b]
links: []
created: 2026-04-07T20:18:38Z
type: task
priority: 2
assignee: cristos
parent: rk-ss1i
tags: [spec:SPEC-052]
---
# Add validation hooks for each workflow step

Implement validation: sidecar existence test, reference resolution grep, specwatch.sh scan — all must pass before loop exits.


## Notes

**2026-04-07T20:38:08Z**

Validation hooks implementation complete: validate-workflow-step.sh created earlier with validation functions for all 9 workflow steps. Each function checks specific preconditions (file exists, frontmatter present, parent artifacts exist, adr-check passes, specwatch clean). Script returns 0 on pass, 1 on fail, 2 on invalid args.
