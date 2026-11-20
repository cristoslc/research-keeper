# Tech stack

## Language and toolchain

| Area | Choice |
|---|---|
| Language | Python 3.11 or newer (`requires-python = ">=3.11"`) |
| Package and environment manager | uv (`uv.lock` is committed) |
| Build backend | hatchling |
| Test runner | pytest, with `pytest-tmp-files` |
| Type checking | pyright, configured by `pyrightconfig.json` (`.venv` at the repo root) |
| Secret scanning | gitleaks, through pre-commit (`.pre-commit-config.yaml`) |

## Core libraries

Declared in `pyproject.toml`.

| Library | Used for |
|---|---|
| click | CLI framework (`rk` entry point is `research_keeper.cli:main`) |
| jinja2 | Sidecar templates |
| pyyaml | Library config and per-node metadata |
| httpx | HTTP, including the Ollama embeddings client |
| trafilatura, playwright | Web page extraction, and a browser fallback for JavaScript-heavy pages |
| yt-dlp | Video and audio download |
| magic-wormhole | The `wormhole:` input transport |
| psutil | Lock and process checks |
| tqdm | Progress output |

## Optional extras

| Extra | Libraries | Used for |
|---|---|---|
| `media` | faster-whisper, paddleocr | Speech transcripts and burned-in subtitle OCR |
| `documents` | pymupdf, pymupdf4llm | PDF and document-to-markdown conversion |
| `mcp` | mcp | The `rk serve` MCP server |
| `all` | all of the above | Full install |

## Storage

- Library: plain files and directories (markdown, YAML, symlinks), kept in a git repo the user owns.
- Index: SQLite (`rk.db`) with an `nodes` table, an `edges` table, an `embeddings` table, and an FTS5 virtual table `node_search`. It is derived and rebuilt by `rk rebuild`.
- Large binaries: Git LFS, configured in the library by `rk init`.

## External services and tools

| System | Role | Required |
|---|---|---|
| Ollama (`http://localhost:11434`, default model `nomic-embed-text`) | Embeddings for semantic search | No; without it, search degrades and `rk doctor` reports missing embeddings |
| QMD | Optional retriever, called as a subprocess | No |
| ffmpeg / ffprobe | Media handling | Only for media sources |
| Chromium via Playwright | Site crawling and fallback fetch | Only for crawling |
| Git remote | `rk sync` and `rk publish` for shared libraries | No |

## Infrastructure

- Source hosting: GitHub (`cristoslc/research-keeper`). Dependabot opens dependency update branches. The repo has no CI workflow files; tests run locally with `uv run pytest`.
- Distribution: the README installs from the git repo with `uv tool install`, and `rk update` updates either that install or a dev clone.
- Observability: Python `logging` to stderr; `--verbose` prints full tracebacks. There is no telemetry.
