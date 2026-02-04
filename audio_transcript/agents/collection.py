"""
Agents dedicated to cross-participant / collection-level analysis.
"""

from __future__ import annotations

from typing import Dict, List

from ..config import get_settings
from ..utils import load_json_from_text, response_to_text
from .base import AgentBase


class CollectionSummaryAgent(AgentBase):
    def __init__(self) -> None:
        settings = get_settings()
        prompt = (
            "You analyze a set of participant profiles (each already summarized). "
            "Produce a cohesive overview of the entire collection, note cross-participant patterns, "
            "and flag notable tensions. Output JSON with keys "
            "`overall_summary` (paragraph) and `notable_patterns` (array of short bullet strings)."
        )
        super().__init__(system_prompt=prompt, model=settings.models.reasoning, temperature=0.2)

    def summarize(self, participants_context: str) -> Dict[str, object]:
        response = self._run(participants_context)
        return load_json_from_text(response_to_text(response))


class CollectionThemeAgent(AgentBase):
    def __init__(self) -> None:
        settings = get_settings()
        prompt = (
            "You are the cross-interview theme agent. Given participant profiles, "
            "identify 3-6 themes spanning multiple participants. For each theme provide: "
            "`name`, `description`, `participants` (list of participant IDs), "
            "`supporting_quotes` (array of {participant_id, quote, source_file}). "
            "All quotes must keep participant IDs (e.g., P1, P2). Return JSON with top-level key `themes`."
        )
        super().__init__(system_prompt=prompt, model=settings.models.reasoning, temperature=0.2)

    def extract(self, participants_context: str) -> Dict[str, object]:
        response = self._run(participants_context)
        return load_json_from_text(response_to_text(response))


class CollectionQuoteAgent(AgentBase):
    def __init__(self) -> None:
        settings = get_settings()
        prompt = (
            "You surface standout quotes across multiple participants. "
            "Return JSON with key `quotes`, an array of objects: "
            "{participant_id, quote, category, insight}. "
            "Categories can be `insight`, `contradiction`, or `emotion`. "
            "Always mention participant IDs."
        )
        super().__init__(system_prompt=prompt, model=settings.models.reasoning, temperature=0.2)

    def highlight(self, participants_context: str) -> Dict[str, object]:
        response = self._run(participants_context)
        return load_json_from_text(response_to_text(response))

