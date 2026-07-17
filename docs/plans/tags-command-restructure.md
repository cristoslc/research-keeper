# Plan: Restructure `rk tags` to Group with Subcommands

## Motivation

The current CLI is flat (`rk tags`, `rk sources`, etc.) with no noun-verb grouping, except for `skill` and `auth` which are already `@main.group()` with subcommands. Converting `tags` to a group:

- Matches the existing `skill`/`auth` pattern.
- Scales to future tag operations (`tags create`, `tags delete`, `tags rename`).
- Allows `rk tags list --sort sources-desc` naturally.

## Design

### Before

```
rk tags --root <path>                    # flat command, alpha sort only
```

### After

```
rk tags list [--root <path>] [--sort alpha|sources-asc|sources-desc]
rk tags                                  # same as `rk tags list` (default subcommand)
```

The `list` subcommand is **the default** — invoking `rk tags` with no subcommand falls through to `rk tags list`.

### `--sort` option values

| Value | Behavior |
|-------|----------|
| `alpha` (default) | Alphabetical by tag slug |
| `sources-asc` | Ascending by source count |
| `sources-desc` | Descending by source count |
| `updated-asc` | Ascending by `last_synthesized` timestamp (oldest first; never-synthesized tags sort first) |
| `updated-desc` | Descending by `last_synthesized` timestamp (newest first; never-synthesized tags sort last) |

### Output format

No change from current:

```
  tag-name (N sources) [+/-]
```

The user can pipe to `head` for limiting (no `--limit` needed if that's the only use case).

## Changes Required

### 1. `src/research_keeper/cli.py` — Replace the flat `tags` command

**Remove** (lines ~800-823):

```python
@main.command()
@click.option("--root", type=click.Path(exists=True), default=".")
def tags(root: str) -> None:
    """List all tags with source counts."""
    # ... current implementation
```

**Add**:

```python
@main.group(invoke_without_command=True)
@click.pass_context
def tags(ctx: click.Context) -> None:
    """List and manage tags."""
    if ctx.invoked_subcommand is None:
        ctx.invoke(tags_list)


@tags.command("list")
@click.option("--root", type=click.Path(exists=True), default=".")
@click.option(
    "--sort",
    type=click.Choice(["alpha", "sources-asc", "sources-desc"]),
    default="alpha",
    help="Sort order for tags (default: alpha)",
)
def tags_list(root: str, sort: str) -> None:
    """List all tags with source counts."""
    try:
        root_path = Path(root).resolve()
        from research_keeper.adapters.filesystem.tag_store import FilesystemTagStore

        tag_store = FilesystemTagStore(root_path)
        tag_list = tag_store.list()

        if not tag_list:
            click.echo("No tags yet.")
            return

        # Build rows for sorting flexibility
        rows: list[tuple[str, int, bool, str | None]] = []
        for tag_slug in tag_list:
            source_slugs = tag_store.sources_for_tag(tag_slug)
            has_synthesis = (tag_store.tag_dir(tag_slug) / "synthesis.md").exists()
            meta = tag_store.get_meta(tag_slug)
            last_syn = (meta or {}).get("last_synthesized")
            rows.append((tag_slug, len(source_slugs), has_synthesis, last_syn))

        if sort == "alpha":
            rows.sort(key=lambda r: r[0])
        elif sort == "sources-asc":
            rows.sort(key=lambda r: (r[1], r[0]))
        elif sort == "sources-desc":
            rows.sort(key=lambda r: (-r[1], r[0]))
        elif sort == "updated-asc":
            rows.sort(key=lambda r: (r[3] or "", r[0]))
        elif sort == "updated-desc":
            rows.sort(key=lambda r: (r[3] or "", r[0]), reverse=True)

        for tag_slug, count, has_synthesis, _last_syn in rows:
            synth_marker = "+" if has_synthesis else "-"
            click.echo(f"  {tag_slug} ({count} sources) [{synth_marker}]")
    except Exception as exc:
        _handle_error(exc)
```

### 2. `tests/test_cli_tags.py` — Update tests

- Rename `test_tags_command_empty` → `test_tags_list_empty`
- Rename `test_tags_command_with_tags` → `test_tags_list_with_tags`
- Change invocation from `["tags", "--root", ...]` to `["tags", "list", "--root", ...]` in both tests
- Add a new test: `test_tags_list_sort_by_sources_desc` that creates tags with different source counts and verifies output order
- Add a new test: `test_tags_list_sort_by_updated_desc` that creates tags with different `last_synthesized` timestamps and verifies output order (newest first)
- Add a new test: `test_tags_list_sort_by_updated_asc` that verifies ascending order by `last_synthesized`
- Add a new test: `test_tags_defaults_to_list` that invokes `["tags", "--root", ...]` (no subcommand) and confirms it works the same as explicit `list`

## Not in Scope

- `--limit` / `head` support — the user can pipe to `head` as requested.
- Other subcommands (`tags create`, `tags delete`, etc.) — future work.
- `rk list tags` variant — the plan settles on `rk tags list`.