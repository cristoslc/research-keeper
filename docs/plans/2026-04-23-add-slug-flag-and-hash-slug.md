# Implementation Plan: add --slug flag and hash-based auto-slug collision handling

**Created:** 2026-04-23
**Priority:** high

---

## Goal

Add a `--slug` flag to `rk add` so callers can manually specify a slug.
Eliminate auto-naming collisions by using a truncated content hash instead of a numeric counter.

## Architecture

- `cli.py`: Add `--slug` click option to `add` command, forward to `pipeline.add(..., slug=...)`.
- `pipeline.py`: `add()` accepts optional `slug` kwarg, passes it to `store.add(..., slug=...)`.
- `source_store.py`: `add()` accepts optional `slug` kwarg. If provided, uses it directly; otherwise generates slug from title with hash suffix if a directory with that slug already exists.

## Files

- Create: none
- Modify:
  - `src/research_keeper/cli.py`
  - `src/research_keeper/pipeline.py`
  - `src/research_keeper/adapters/filesystem/source_store.py`
  - `tests/test_source_store.py`
  - `tests/test_slug_from_title.py`
  - `tests/test_pipeline.py`
  - `tests/test_smoke.py`

---

### Task 1: Write failing test for hash-based unique slug.

**File:** `tests/test_source_store.py`
**Test name:** `test_slug_collision_uses_hash_suffix`

```python
def test_slug_collision_uses_hash_suffix(library_root: Path):
    store = FilesystemSourceStore(library_root)
    store.add("# Content A", {"title": "Test", "origin": "inline"})
    source_b = store.add("# Content B", {"title": "Test", "origin": "inline"})
    # Slug should include a hash suffix, not just "test-2"
    assert source_b.slug.startswith("test-")
    assert source_b.slug != "test"
    assert source_b.slug != "test-2"
```

**Run:** `uv run pytest tests/test_source_store.py::test_slug_collision_uses_hash_suffix -v`
**Expected:** FAIL - test does not exist yet.

Wait: TDD says write test first, watch it fail with the expected failure (feature missing).

Actually write it first, then run.

---

### Task 2: Implement hash-based collision in `source_store.py`.

**File:** `src/research_keeper/adapters/filesystem/source_store.py`
**Change:** Modify `_unique_slug(self, title)` to append first 6 chars of content hash (passed in).

Wait - `_unique_slug` currently doesn't receive the content hash. We need to pass it.

Change signature to `_unique_slug(self, title: str, content_hash: str) -> str`.

```python
def _unique_slug(self, title: str, content_hash: str) -> str:
    base = slugify(title)
    if not (self._sources_dir / base).exists():
        return base
    # Append first 6 chars of content hash to guarantee uniqueness across different content.
    suffix = content_hash[:6]
    candidate = f"{base}-{suffix}"
    if not (self._sources_dir / candidate).exists():
        return candidate
    # Fallback (same title + same hash = same content, should have been caught by dedup)
    for i in range(2, 100):
        candidate = f"{base}-{suffix}-{i}"
        if not (self._sources_dir / candidate).exists():
            return candidate
    raise ValueError(f"Too many slug collisions for '{base}'")
```

Update `add()` to pass content hash:
```python
slug = self._unique_slug(metadata.get("title", "untitled"), content_hash)
```

**Run:** `uv run pytest tests/test_source_store.py::test_slug_collision_uses_hash_suffix -v`
**Expected:** PASS.

---

### Task 3: Update existing collision test.

The existing `test_slug_collision_appends_suffix` asserts `source_b.slug.startswith("test-")` and `source_b.slug != "test"`, which is still true. We need to update it to match new behavior.

Change `test_slug_collision_appends_suffix` to reflect hash suffix:
```python
def test_slug_collision_appends_suffix(library_root: Path):
    store = FilesystemSourceStore(library_root)
    store.add("# Content A", {"title": "Test", "origin": "inline"})
    source_b = store.add("# Content B", {"title": "Test", "origin": "inline"})
    assert source_b.slug.startswith("test-")
    assert source_b.slug != "test"
```

This already passes because `startswith("test-")` and `!= "test"` are still true.

---

### Task 4: Write failing test for `--slug` CLI flag.

**File:** `tests/test_slug_from_title.py`
**Test name:** `test_cli_slug_flag_sets_slug`

```python
def test_cli_slug_flag_sets_slug(self, runner: CliRunner, tmp_path: Path):
    from research_keeper.cli import main
    with runner.isolated_filesystem() as td:
        target_dir = Path(td) / "test-lib"
        result = runner.invoke(main, ["init", str(target_dir)])
        assert result.exit_code == 0

        result = runner.invoke(main, [
            "add", "--root", str(target_dir),
            "--text", "Custom content here.",
            "--slug", "my-custom-slug",
        ])
        assert result.exit_code == 0
        source_dir = target_dir / "library" / "sources" / "my-custom-slug"
        assert source_dir.exists()
```

**Run:** `uv run pytest tests/test_slug_from_title.py::TestCLIEscapedNewlines::test_cli_slug_flag_sets_slug -v`
**Expected:** FAIL -- `no such option: --slug`

---

### Task 5: Add `--slug` flag to CLI.

**File:** `src/research_keeper/cli.py`

Add option in `add` command decorator:
```python
@click.option(
    "--slug", default=None, help="Override the auto-generated source slug"
)
```

Add parameter to function signature and pass to pipeline.add for both --text and raw source paths.

For `--text` path:
```python
source = pipeline.add(
    actual_content,
    metadata,
    investigation_id=investigation,
    no_prompt=no_prompt,
    slug=slug,
)
```

For raw sources:
```python
source = pipeline.add(
    transport_result.resolved,
    metadata,
    investigation_id=investigation,
    no_prompt=no_prompt,
    slug=slug,
)
```

---

### Task 6: Thread `slug` through pipeline.

**File:** `src/research_keeper/pipeline.py`

Update `add()` signature:
```python
def add(
    self,
    raw: str,
    metadata: dict | None = None,
    investigation_id: str | None = None,
    no_prompt: bool = False,
    slug: str | None = None,
) -> Source:
```

Pass to store:
```python
source = self._store.add(
    content,
    merged,
    original_file=original_file_path,
    slug=slug,
)
```

---

### Task 7: Accept `slug` parameter in source_store.

**File:** `src/research_keeper/adapters/filesystem/source_store.py`

Update `add()` signature:
```python
def add(
    self,
    content: str,
    metadata: dict,
    original_file: Path | None = None,
    slug: str | None = None,
) -> Source:
```

Use provided slug or generate unique:
```python
if slug is not None:
    slug = slugify(slug)
    if (self._sources_dir / slug).exists():
        raise ValueError(f"Slug '{slug}' already exists")
else:
    slug = self._unique_slug(metadata.get("title", "untitled"), content_hash)
```

**Run all source_store tests:**
`uv run pytest tests/test_source_store.py -v`
**Expected:** All pass.

---

### Task 8: Write pipeline test for explicit slug.

**File:** `tests/test_pipeline.py`
**Test name:** `test_add_with_explicit_slug`

```python
def test_add_with_explicit_slug(pipeline: IntakePipeline):
    source = pipeline.add("# My Title\n\nContent", slug="custom-slug")
    assert source.slug == "custom-slug"
```

**Run:** `uv run pytest tests/test_pipeline.py::test_add_with_explicit_slug -v`
**Expected:** PASS.

---

### Task 9: Write failing test for duplicate explicit slug.

**File:** `tests/test_pipeline.py`
**Test name:** `test_add_duplicate_explicit_slug_raises`

```python
def test_add_duplicate_explicit_slug_raises(pipeline: IntakePipeline):
    pipeline.add("# First", slug="custom-slug")
    import pytest
    with pytest.raises(ValueError, match="already exists"):
        pipeline.add("# Second", slug="custom-slug")
```

**Run:** `uv run pytest tests/test_pipeline.py::test_add_duplicate_explicit_slug_raises -v`
**Expected:** PASS.

---

### Task 10: Write BDD smoke tests.

**File:** `tests/test_smoke.py`

Add BDD scenarios:

```python
    def test_rk_add_hash_based_slug_for_collisions(self, rk_root_manual: Path):
        """Given two sources with same title but different content, when added via CLI,
        then slugs are unique and contain hash suffixes."""
        runner = CliRunner()
        result = runner.invoke(main, [
            "add", "--root", str(rk_root_manual), "--no-prompt",
            "--text", "First document body here.",
            "--origin", "https://example.com/first",
        ])
        assert result.exit_code == 0
        result2 = runner.invoke(main, [
            "add", "--root", str(rk_root_manual), "--no-prompt",
            "--text", "Second document body here.",
            "--origin", "https://example.com/second",
        ])
        assert result2.exit_code == 0
        sources_dir = rk_root_manual / "library" / "sources"
        # Should have two distinct directories, neither ending in plain numeric -2
        dirs = [d.name for d in sources_dir.iterdir() if d.is_dir()]
        assert len(dirs) == 2
        assert dirs[0] != dirs[1]

    def test_rk_add_with_explicit_slug(self, rk_root_manual: Path):
        """Given --slug my-article, when rk add is called, then source is filed under that slug."""
        runner = CliRunner()
        result = runner.invoke(main, [
            "add", "--root", str(rk_root_manual), "--no-prompt",
            "--text", "Explicit slug content.",
            "--slug", "my-article",
        ])
        assert result.exit_code == 0
        source_dir = rk_root_manual / "library" / "sources" / "my-article"
        assert source_dir.is_dir()
        assert (source_dir / "source.md").exists()
```

---

### Task 11: Run full test suite.

```bash
uv run pytest tests/ -v
```

Expected: All pass.

### Task 12: Smoke test.

```bash
rm -rf /tmp/rk-slug-test
rk init /tmp/rk-slug-test
rk add --root /tmp/rk-slug-test --no-prompt --text "First doc"
rk add --root /tmp/rk-slug-test --no-prompt --text "Second doc"
ls /tmp/rk-slug-test/library/sources/
rk add --root /tmp/rk-slug-test --no-prompt --text "Custom" --slug my-slug
ls /tmp/rk-slug-test/library/sources/
rm -rf /tmp/rk-slug-test
```

---

## Definition of Done

- [ ] `rk add --slug my-slug` files source under `library/sources/my-slug/`.
- [ ] Same title with different content gets unique slugs via hash suffix, not numeric suffix.
- [ ] Explicit slug collision raises clear error.
- [ ] All existing tests pass.
- [ ] New unit and BDD tests pass.
- [ ] Smoke test succeeds.
