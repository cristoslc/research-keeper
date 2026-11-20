# Staging scripts

research-keeper is a local CLI with no server, so "staging" means a throwaway install of a branch that gets smoke-tested and then removed. The identity of a staging instance is its branch name.

| Script | Does |
|---|---|
| `deploy.sh <branch>` | Exports the branch with `git archive`, builds a virtualenv, installs the package (core dependencies only), and prints the staging directory |
| `e2e.sh <staging-dir>` | Runs `rk init`, `rk add --text`, a duplicate add, `rk keyword-search`, `rk rebuild`, and `rk doctor` with the staged binary. Offline; no Ollama needed. `rk init` may provision Playwright Chromium on a machine that lacks it. Exits non-zero on the first failure |
| `teardown.sh <staging-dir>` | Deletes the staging directory. Refuses directories that `deploy.sh` did not create |

```bash
stage=$(scripts/staging/deploy.sh trunk)
scripts/staging/e2e.sh "$stage"
scripts/staging/teardown.sh "$stage"
```

The smoke test covers the intake and index path. It does not cover media transcription, the browser fallback, or semantic search, which need the optional extras or external services; those are covered by the pytest suite and by manual runs.
