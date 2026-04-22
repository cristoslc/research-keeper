# Subagent Prompt Templates for SPEC-052

These templates are used by `discovery-loop.sh` to guide lower-weight models (gemma4, phi) through the artifact creation workflow. Each template includes explicit step-by-step instructions with confirmation requirements.

## Base Template (Iteration 1)

```
Create a {{ARTIFACT_TYPE}} artifact with title: {{TITLE}}.

Follow the swain-design SKILL.md workflow completely. All steps must be executed in order:

1. Run next-artifact-number script to get the artifact ID
2. Read the artifact definition file from references/
3. Read the artifact template from references/
4. Create the phase directory with mkdir -p
5. Write the primary markdown file with frontmatter
6. Run resolve-artifact-loop.sh to hyperlink all references
7. Validate parent artifact references exist
8. Run adr-check.sh for compliance
9. Run specwatch.sh scan

After completing all steps, run workflow-step-tracker.sh validate to confirm.
```

## Refined Template (Iterations 2-4)

```
Create a {{ARTIFACT_TYPE}} artifact with title: {{TITLE}}.

IMPORTANT: You must complete ALL workflow steps in order. Missing steps from previous attempt:
{{MISSING_STEPS}}

Execute these steps SEQUENTIALLY. After EACH step, reply with 'STEP <N> COMPLETE' before continuing:

STEP 1: Run next-artifact-number script to get the artifact ID
  → Reply: "STEP 1 COMPLETE"

STEP 2: Read the artifact definition file from references/
  → Reply: "STEP 2 COMPLETE"

STEP 3: Read the artifact template from references/
  → Reply: "STEP 3 COMPLETE"

STEP 4: Create the phase directory with mkdir -p
  → Reply: "STEP 4 COMPLETE"

STEP 5: Write the primary markdown file with frontmatter
  → Reply: "STEP 5 COMPLETE"

STEP 6: Run resolve-artifact-loop.sh to hyperlink all references
  → Reply: "STEP 6 COMPLETE"

STEP 7: Validate parent artifact references exist
  → Reply: "STEP 7 COMPLETE"

STEP 8: Run adr-check.sh for compliance
  → Reply: "STEP 8 COMPLETE"

STEP 9: Run specwatch.sh scan
  → Reply: "STEP 9 COMPLETE"

After step 9, run workflow-step-tracker.sh validate to confirm all steps executed.

DO NOT skip any steps. DO NOT proceed to the next step until the current one completes.
```

## Critical Template (Iteration 5+)

```
CRITICAL: This is iteration {{ITERATION}}. Previous attempts failed to complete all workflow steps.

Create a {{ARTIFACT_TYPE}} artifact with title: {{TITLE}}.

You MUST complete every step listed below. If you cannot complete a step, report an EXPLICIT ERROR
with the step name and reason. Do NOT silently skip steps.

STEP 1: Run next-artifact-number script to get the artifact ID
  → Reply: "STEP 1 COMPLETE" or "ERROR STEP 1: <reason>"

STEP 2: Read the artifact definition file from references/
  → Reply: "STEP 2 COMPLETE" or "ERROR STEP 2: <reason>"

STEP 3: Read the artifact template from references/
  → Reply: "STEP 3 COMPLETE" or "ERROR STEP 3: <reason>"

STEP 4: Create the phase directory with mkdir -p
  → Reply: "STEP 4 COMPLETE" or "ERROR STEP 4: <reason>"

STEP 5: Write the primary markdown file with frontmatter
  → Reply: "STEP 5 COMPLETE" or "ERROR STEP 5: <reason>"

STEP 6: Run resolve-artifact-loop.sh to hyperlink all references
  → Reply: "STEP 6 COMPLETE" or "ERROR STEP 6: <reason>"

STEP 7: Validate parent artifact references exist
  → Reply: "STEP 7 COMPLETE" or "ERROR STEP 7: <reason>"

STEP 8: Run adr-check.sh for compliance
  → Reply: "STEP 8 COMPLETE" or "ERROR STEP 8: <reason>"

STEP 9: Run specwatch.sh scan
  → Reply: "STEP 9 COMPLETE" or "ERROR STEP 9: <reason>"

FAILURE TO COMPLETE:
If you cannot complete this artifact creation, explicitly state:
"UNABLE TO COMPLETE: <reason>"

This allows the orchestrator to escalate to a human operator.
```

## Usage in discovery-loop.sh

The `build_refined_prompt()` function selects the appropriate template based on iteration count:

- **Iteration 1:** Base template
- **Iterations 2-4:** Refined template with missing steps injected
- **Iteration 5+:** Critical template with error reporting requirements

## Confirmation Parsing

The orchestrator parses subagent output for confirmation patterns:

```bash
# Check for step completion
if echo "$output" | grep -q "STEP $n COMPLETE"; then
  echo "Step $n confirmed complete"
elif echo "$output" | grep -q "ERROR STEP $n:"; then
  echo "Step $n failed with error"
  record_failure "$n"
else
  echo "Step $n confirmation missing — assuming skipped"
  record_skip "$n"
fi
```

## Model-Specific Adaptations

### gemma4

- Requires very explicit step boundaries
- Benefits from "Reply: 'STEP N COMPLETE'" pattern
- Tends to skip validation steps — emphasize steps 8-9

### phi

- More likely to ask clarifying questions
- Include "If unsure, proceed with best guess" guidance
- Better at following multi-step instructions than gemma4

### Higher-tier models (not using discovery loop)

- Use base template only
- No confirmation requirements needed
- Trust model to complete workflow autonomously
