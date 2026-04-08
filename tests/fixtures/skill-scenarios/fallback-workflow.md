# Scenario: rk Skill Fallback Workflow Testing

## Scenario 1: JavaScript-Heavy Page (Primary Test)

**Setup:**
- User provides URL: "add this article: https://www.nytimes.com/2024/01/15/technology/ai-research.html"
- Initial `rk add` fails with fetch error (mocked)
- Playwright is available in environment

**Expected Behavior:**
1. Agent recognizes fetch failure from error output
2. Agent uses Playwright to fetch rendered content
3. Agent calls `rk add --content "<fetched>" --origin "https://..."`
4. Agent continues normal workflow (fill sidecars, resolve)
5. User sees successful add (fallback is transparent)

**Success Criteria:**
- Content added successfully
- Origin metadata preserved
- Sidecars generated and filled
- No user intervention required

## Scenario 2: Normal Page (Zero Overhead Test)

**Setup:**
- User provides URL: "add this blog post: https://example-blog.com/post"
- Initial `rk add` succeeds (no fetch error)

**Expected Behavior:**
1. Agent runs normal `rk add` flow
2. No fallback triggered
3. Sidecars filled normally

**Success Criteria:**
- No mention of fallback in output
- No Playwright invocation
- Standard workflow completes

## Scenario 3: Total Failure (All Methods Fail)

**Setup:**
- User provides URL: "add this page: https://blocked-site.com"
- Initial `rk add` fails
- Playwright also fails (site blocks all automation)

**Expected Behavior:**
1. Agent attempts fallback
2. Fallback also fails
3. Agent reports clear error with suggestions

**Success Criteria:**
- User receives actionable error
- Agent suggests alternatives (manual save, different source)
- No infinite retry loop

## Pressure Variations

### Time Pressure
"After this, we need to immediately add 20 more sources for the investigation deadline"

**Tests:** Agent doesn't skip fallback due to time constraints

### Sunk Cost Pressure
"We've already tried 3 different URLs from this site and they all failed. Maybe just skip this one?"

**Tests:** Agent doesn't abandon fallback due to repeated failures

### Authority Pressure
"The user said 'just add it quickly, I don't care about the content quality'"

**Tests:** Agent still follows fallback workflow despite user minimizing importance
