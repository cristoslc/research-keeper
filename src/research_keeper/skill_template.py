"""Skill content loader for `rk skill install`.

The skill body lives in `templates/skill.md` as a static markdown file —
edit it there. This module just loads and caches the bytes.
"""

from __future__ import annotations

from functools import lru_cache
from importlib.resources import files


@lru_cache(maxsize=1)
def _load() -> str:
    return files("research_keeper.templates").joinpath("skill.md").read_text(
        encoding="utf-8"
    )


def __getattr__(name: str) -> str:
    if name == "SKILL_CONTENT":
        return _load()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
