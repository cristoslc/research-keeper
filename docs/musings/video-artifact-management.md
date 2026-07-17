# Video Artifact Management & Binary Safety

**Date:** 2026-07-16
**Issue:** #48
**Status:** Musing → Plan

## The Problem

`rk add` on a video URL (YouTube, Instagram, TikTok) extracts text and a screenshot but discards the video. The user must download separately with yt-dlp. Meanwhile, rk already stores binaries (screenshots, PDFs, DOCX) in git with no LFS tracking — a latent bloat problem that video makes acute.

## Design Decisions (from parley)

### Video download: opt-out, not opt-in
- yt-dlp moves from `media` extra to core dependency
- `rk add` downloads video by default for any URL classified as `media`
- `--no-video` flag and config-level `video.enabled: false` to disable
- No size cap — user decides what to keep

### LFS: init-time setup, not afterthought
- `rk init` installs git-lfs (platform-aware: brew/apt/dnf/winget/choco)
- Runs `git lfs install` in the new repo
- Writes `.gitattributes` tracking all binary types:
  - Documents: `*.pdf`, `*.docx`, `*.pptx`, `*.xlsx`
  - Images: `*.jpg`, `*.jpeg`, `*.png`, `*.gif`
  - Video: `*.mp4`, `*.webm`, `*.mkv`, `*.mov`
  - Audio: `*.mp3`, `*.wav`, `*.m4a`, `*.flac`, `*.ogg`
- Stages and commits `.gitattributes` as part of the initial commit
- If LFS install fails: pre-commit hook as safety net

### Pre-commit hook: Python, not shell
- Written in Python for cross-platform (Windows/Linux/macOS)
- Checks staged files >100KB against LFS patterns in `.gitattributes`
- Rejects with clear message if a large binary isn't LFS-tracked
- Can be bypassed with `git commit --no-verify` (user's choice, repo bloats)

### rk doctor: LFS health check
- On `rk update`, doctor runs and detects missing LFS config
- Asks: "LFS not configured. Set it up? [Y/n]"
- On yes: install + init + .gitattributes + commit
- Also checks for committed binaries that should be LFS-tracked

### Cross-platform LFS install
- macOS: `brew install git-lfs`
- Linux: `apt install git-lfs` / `dnf install git-lfs` / `yum install git-lfs`
- Windows: `winget install GitHub.GitLFS` → `choco install git-lfs`
- Fallback: print platform-specific manual install URL

### Manifest changes
- `video_file: video.mp4` in manifest.yaml when video is downloaded
- `video_format`, `video_size` optional metadata

## Open Questions (resolved)

- **Cap?** No cap. User decides what to keep.
- **Safety if LFS fails?** Pre-commit hook catches large binaries.
- **Existing repos upgrading?** `rk update` → `rk doctor` → one-time setup flow.
- **Should init commit .gitattributes?** Yes. Full repo standup is rk init's job.
- **Should doctor autofix?** No. Ask the user yes/no.

## What's Next

Implementation plan covering:
1. Config: `VideoConfig` with `enabled: true`
2. CLI: `--no-video` flag on `rk add`
3. Pipeline: persist video file alongside source.md
4. Normalizer: return video path in metadata
5. Init: LFS install + .gitattributes + pre-commit hook
6. Doctor: LFS health check + fix flow
7. Dependencies: yt-dlp to core
8. Tests for all of the above
