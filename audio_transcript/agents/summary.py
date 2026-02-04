"""
Summary agent producing short + long summaries.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..config import get_settings
from ..utils import load_json_from_text, response_to_text
from .base import AgentBase


@dataclass
class SummaryResult:
    short_summary: str
    long_summary: str


SUMMARY_FORMAT = """
Return valid JSON with this exact shape:
{
  "short_summary": "3-4 sentence highlight reel",
  "long_summary": "One paragraph synthesis"
}
"""


class SummaryAgent(AgentBase):
    def __init__(self) -> None:
        settings = get_settings()
        super().__init__(
            system_prompt=(
                "You are the summary agent in a qualitative research pipeline. "
                "Blend narrative clarity with factual accuracy when summarizing interviews. "
                "Always respond with compact JSON following: "
                + SUMMARY_FORMAT
            ),
            model=settings.models.reasoning,
        )

    def summarize(self, transcript: str, *, rag_context: Optional[str] = None) -> SummaryResult:
        prompt = [
            "Produce both a short and a long summary for the provided transcript.",
            "Transcript:",
            transcript,
        ]
        if rag_context:
            prompt.extend(
                [
                    "",
                    "Reference Context (optional):",
                    rag_context,
                    "",
                    "Use the context only for comparisons or recurring themes.",
                ]
            )
        payload = "\n".join(prompt)
        response = self._run(payload)
        data = load_json_from_text(response_to_text(response))
        return SummaryResult(**data)
