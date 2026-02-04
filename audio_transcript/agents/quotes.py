"""
Agent that highlights memorable or emotionally salient quotes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from ..config import get_settings
from ..utils import load_json_from_text, response_to_text
from .base import AgentBase


@dataclass
class QuoteHighlight:
    quote: str
    category: str
    rationale: str
    suggested_use: str


@dataclass
class QuoteHighlights:
    highlights: List[QuoteHighlight]


QUOTE_FORMAT = """
Return JSON:
{
  "highlights": [
    {
      "quote": "...",
      "category": "memorable|emotional|behavioral",
      "rationale": "...",
      "suggested_use": "..."
    }
  ]
}
Provide 3-8 total quotes with at least one per category when possible.
"""


class QuoteHighlighterAgent(AgentBase):
    def __init__(self) -> None:
        settings = get_settings()
        super().__init__(
            system_prompt=(
                "You are tasked with surfacing memorable, emotionally salient, "
                "and behavior-describing quotes for researchers. "
                "Always respond with JSON formatted like:\n"
                + QUOTE_FORMAT
            ),
            model=settings.models.reasoning,
        )

    def _build_prompt(self, transcript: str, *, force_json: bool = False, previous_output: str | None = None) -> str:
        lines = []
        if force_json:
            lines.extend(
                [
                    "Your previous response was not valid JSON.",
                    "Respond again using ONLY valid JSON matching the required schema.",
                    "Do not include explanations, markdown fences, or commentary.",
                ]
            )
            if previous_output:
                lines.extend(
                    [
                        "",
                        "Previous invalid response (for reference only):",
                        previous_output,
                    ]
                )
            lines.append("")
        lines.extend(
            [
                "Identify 3-8 standout quotes.",
                "Include at least one per category if possible: memorable, emotional, behavioral.",
                "Provide a quick rationale and suggested downstream use.",
                "",
                "Transcript:",
                transcript,
            ]
        )
        return "\n".join(lines)

    def _run_with_retry(self, transcript: str) -> QuoteHighlights:
        prompt = self._build_prompt(transcript)
        response = self._run(prompt)
        raw = response_to_text(response)
        try:
            parsed = load_json_from_text(raw)
        except ValueError:
            retry_prompt = self._build_prompt(
                transcript, force_json=True, previous_output=raw
            )
            retry_response = self._run(retry_prompt)
            retry_raw = response_to_text(retry_response)
            parsed = load_json_from_text(retry_raw)
        return QuoteHighlights(
            highlights=[QuoteHighlight(**highlight) for highlight in parsed["highlights"]]
        )

    def highlight(self, transcript: str) -> QuoteHighlights:
        return self._run_with_retry(transcript)
