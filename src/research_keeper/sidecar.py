# src/research_keeper/sidecar.py
"""Sidecar template generation and response parsing (SPEC-028).

Generates .j2 template files that agents render to produce completed outputs.
Parses rendered outputs (tag.yaml, synthesize.md) for rk resolve.
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml

from research_keeper.config import CompletionConfig
from research_keeper.slugify import slugify


class SidecarGenerator:
    """Generate sidecar templates and parse rendered responses."""

    def __init__(self, root: Path, completion_config: CompletionConfig | None = None) -> None:
        self._root = root
        self._completion = completion_config or CompletionConfig()

    def generate_tag_sidecar(
        self,
        source_slug: str,
        source_content: str,
        existing_tags: list[str],
        model_hint: str,
    ) -> Path:
        """Write a tag.j2 sidecar template for a source.

        Returns the path to the generated .j2 file.
        """
        pending_dir = self._root / "library" / "sources" / source_slug / ".pending"
        pending_dir.mkdir(parents=True, exist_ok=True)

        existing_tags_str = ", ".join(existing_tags) if existing_tags else "(none yet)"

        template = (
            f"{{# rk:tag | model_hint: {model_hint} | target: {source_slug} #}}\n"
            "{#\n"
            "Analyze the content and produce tags.\n"
            "\n"
            f"Existing tags in use: {existing_tags_str}\n"
            "\n"
            "Content:\n"
            f"{source_content}\n"
            "\n"
            "Rules:\n"
            "- 3-7 tags, lowercase hyphenated slugs\n"
            "- Prefer reusing existing tags when they apply\n"
            "- Avoid overly generic tags like \"technology\" or \"research\"\n"
            "#}\n"
            "tags:\n"
            "{% for tag in tags %}\n"
            "  - {{ tag }}\n"
            "{% endfor %}\n"
        )

        path = pending_dir / "tag.j2"
        path.write_text(template)
        return path

    def generate_synthesis_sidecar(
        self,
        tag_slug: str,
        sources: list[dict],
        model_hint: str,
    ) -> Path:
        """Write a synthesize.j2 sidecar template for a tag.

        sources: list of dicts with 'slug' and 'content' keys.
        Returns the path to the generated .j2 file.
        """
        pending_dir = self._root / "tags" / tag_slug / ".pending"
        pending_dir.mkdir(parents=True, exist_ok=True)

        sources_text = ""
        for src in sources:
            sources_text += f"\nSource: {src['slug']}\n{src['content']}\n"

        template = (
            f"{{# rk:synthesize | model_hint: {model_hint} | target: {tag_slug} #}}\n"
            "{#\n"
            f'Synthesize the following sources about "{tag_slug}" into thematic markdown.\n'
            "Organize by theme, not by source. Cite sources by slug in parentheses.\n"
            "Surface agreements, disagreements, and gaps.\n"
            f"{sources_text}"
            "#}\n"
            "{{ synthesis }}\n"
        )

        path = pending_dir / "synthesize.j2"
        path.write_text(template)
        return path

    def generate_query_sidecar(
        self,
        query_id: str,
        query_text: str,
        scored_sources: list[dict],
        model_hint: str,
    ) -> Path:
        """Write a query.j2 sidecar template for a search query.

        scored_sources: list of dicts with 'slug', 'content', 'score',
                        'similarity', 'freshness_weight' keys.
        Returns the path to the generated .j2 file.
        """
        pending_dir = self._root / "queries" / query_id / ".pending"
        pending_dir.mkdir(parents=True, exist_ok=True)

        sources_text = ""
        for src in scored_sources:
            sources_text += (
                f"\nSource: {src['slug']} (score: {src['score']:.2f})\n"
                f"{src['content']}\n"
            )

        template = (
            f"{{# rk:query | model_hint: {model_hint} | target: {query_id} #}}\n"
            "{#\n"
            "Synthesize an answer to the following question using ONLY the sources below.\n"
            "Organize by theme, not by source. Cite sources by slug in parentheses.\n"
            "Surface agreements, disagreements, and gaps.\n"
            "\n"
            f"Question: {query_text}\n"
            f"{sources_text}"
            "#}\n"
            "{{ synthesis }}\n"
        )

        path = pending_dir / "query.j2"
        path.write_text(template)
        return path

    def generate_investigation_sidecar(
        self,
        inv_id: str,
        topic: str,
        brief: str,
        sources_content: list[dict],
        query_syntheses: list[dict],
        prior_synthesis: str | None,
        model_hint: str,
    ) -> Path:
        """Write a synthesize.j2 sidecar for an investigation rolling synthesis.

        sources_content: list of dicts with 'slug' and 'content' keys.
        query_syntheses: list of dicts with 'query_id', 'query_text', 'synthesis' keys.
        Returns the path to the generated .j2 file.
        """
        pending_dir = self._root / "investigations" / inv_id / ".pending"
        pending_dir.mkdir(parents=True, exist_ok=True)

        context_text = ""
        if sources_content:
            context_text += "\nLinked sources:\n"
            for src in sources_content:
                context_text += f"\nSource: {src['slug']}\n{src['content']}\n"

        if query_syntheses:
            context_text += "\nLinked query syntheses:\n"
            for q in query_syntheses:
                context_text += f"\nQuery: {q['query_text']}\n{q['synthesis']}\n"

        prior_text = ""
        if prior_synthesis:
            prior_text = f"\nPrior synthesis (update, don't repeat):\n{prior_synthesis}\n"

        template = (
            f"{{# rk:investigation | model_hint: {model_hint} | target: {inv_id} #}}\n"
            "{#\n"
            f"Rolling synthesis for investigation: {topic}\n"
            f"Brief: {brief}\n"
            f"{context_text}"
            f"{prior_text}"
            "\n"
            "Synthesize a comprehensive overview of this investigation's findings.\n"
            "Organize by theme, not by source. Cite sources and queries by slug.\n"
            "Surface agreements, disagreements, gaps, and open questions.\n"
            "#}\n"
            "{{ synthesis }}\n"
        )

        path = pending_dir / "synthesize.j2"
        path.write_text(template)
        return path

    def parse_tag_response(self, path: Path) -> list[str]:
        """Parse a rendered tag.yaml file, extracting tags with robust handling.

        Handles: clean YAML, numbered lists, bullet lists, comma-separated,
        preamble text, and messy LLM output.
        """
        raw = path.read_text().strip()
        if not raw:
            return []

        # Try YAML parse first
        try:
            data = yaml.safe_load(raw)
            if isinstance(data, dict) and "tags" in data:
                raw_tags = data["tags"]
                if isinstance(raw_tags, list):
                    return self._slugify_and_dedup(raw_tags)
        except yaml.YAMLError:
            pass

        # Try finding a YAML block with 'tags:' in it
        lines = raw.split("\n")
        tag_section_start = None
        for i, line in enumerate(lines):
            if line.strip() == "tags:":
                tag_section_start = i
                break

        if tag_section_start is not None:
            tag_lines = []
            for line in lines[tag_section_start + 1:]:
                stripped = line.strip()
                if stripped.startswith("- "):
                    tag_lines.append(stripped[2:].strip())
                elif stripped and not stripped.startswith("#"):
                    break  # End of tag list
                elif not stripped:
                    continue
            if tag_lines:
                return self._slugify_and_dedup(tag_lines)

        # Fallback: parse as free-form text (numbered lists, bullets, commas)
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # Skip preamble lines ending with ":"
            if line.endswith(":") and not re.match(r"^[\d.\-*]+", line):
                continue
            # Strip numbered list markers
            line = re.sub(r"^\d+[.)]\s*", "", line)
            # Strip bullet markers
            line = re.sub(r"^[-*]\s+", "", line)
            # Strip quotes and backticks
            line = line.strip("`\"'")
            if line:
                cleaned_lines.append(line)

        # Rejoin and split on commas
        rejoined = ", ".join(cleaned_lines)
        raw_tags = [t.strip() for t in rejoined.split(",") if t.strip()]
        return self._slugify_and_dedup(raw_tags)

    def parse_synthesis_response(self, path: Path) -> str:
        """Read a rendered synthesize.md as-is."""
        return path.read_text()

    def _slugify_and_dedup(self, raw_tags: list) -> list[str]:
        """Slugify tags, filter invalid ones, and deduplicate."""
        slugified = [slugify(str(t)) for t in raw_tags]
        valid = [t for t in slugified if t and t != "untitled"]
        seen: set[str] = set()
        deduped: list[str] = []
        for t in valid:
            if t not in seen:
                seen.add(t)
                deduped.append(t)
        return deduped

    def write_intake_lock(self, source_slug: str) -> Path:
        """Write an intake.lock file for a source being processed."""
        import datetime
        import os

        pending_dir = self._root / "library" / "sources" / source_slug / ".pending"
        pending_dir.mkdir(parents=True, exist_ok=True)

        lock_content = (
            "task: intake\n"
            f"started: {datetime.datetime.now(datetime.UTC).isoformat()}\n"
            f"pid: {os.getpid()}\n"
        )

        path = pending_dir / "intake.lock"
        path.write_text(lock_content)
        return path

    def remove_intake_lock(self, source_slug: str) -> None:
        """Remove the intake.lock for a source."""
        lock_path = (
            self._root / "library" / "sources" / source_slug / ".pending" / "intake.lock"
        )
        if lock_path.exists():
            lock_path.unlink()
