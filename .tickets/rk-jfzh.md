---
id: rk-jfzh
status: closed
deps: [rk-s0e8]
links: []
created: 2026-04-07T20:18:35Z
type: task
priority: 2
assignee: cristos
parent: rk-ss1i
tags: [spec:SPEC-052]
---
# Add post-step validation hooks

Add validation hooks that gate progression — each workflow step must pass validation before the next begins.


## Notes

**2026-04-07T20:34:57Z**

Added post-step validation hooks: validate-workflow-step.sh script with validation functions for each workflow step (next-artifact-number, read-definition, read-template, create-phase-directory, write-primary-file, hyperlink-references, validate-parents, adr-check, specwatch-scan). Each step now gates progression — validation must pass before next step proceeds.
