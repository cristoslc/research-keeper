from __future__ import annotations

import logging
import re
from typing import Callable

logger = logging.getLogger(__name__)

HYDE_PROMPT = """You are expanding a search query for a research knowledge base.

Given the query below, generate 8-12 related search terms that would help find relevant documents.

Rules:
- Output ONLY space-separated terms, no punctuation, no explanations
- Include synonyms, related concepts, acronyms, and broader/narrower terms
- Prefer technical terms a researcher would use
- Do not repeat words from the original query

Query: {query}

Expanded terms:"""


class HYDEExpander:
    """Expands a query using HYDE (LLM-generated related terms) for FTS.

    When an LLM completion function is available, it generates 8-12
    related terms via the HYDE_PROMPT template. When no LLM is available
    (or the call fails), expand_query returns the original query unchanged,
    falling back to plain keyword search.
    """

    def __init__(
        self,
        complete_fn: Callable[[str], str] | None = None,
    ):
        self._complete = complete_fn

    def expand_query(self, query: str) -> str:
        if self._complete is None:
            return query

        try:
            prompt = HYDE_PROMPT.format(query=query)
            expanded = self._complete(prompt)
            sanitized = _sanitize_hyde_output(expanded)
            if not sanitized:
                return query
            return sanitized
        except Exception:
            logger.debug("HYDE expansion failed, using original query", exc_info=True)
            return query


def _sanitize_hyde_output(raw: str) -> str:
    """Clean LLM output for FTS consumption.

    Strips punctuation, lowercases, and removes duplicate words
    while preserving word order. Returns "" if no valid terms remain.
    """
    cleaned = re.sub(r"[^a-zA-Z0-9\s]", " ", raw)
    terms = cleaned.lower().split()
    return " ".join(dict.fromkeys(terms))
