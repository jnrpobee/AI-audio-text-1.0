"""
Theme extraction agent for qualitative insights.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from ..config import get_settings
from ..utils import load_json_from_text, response_to_text
from .base import AgentBase


@dataclass
class Theme:
    name: str
    description: str
    frequency: str
    representative_quotes: List[str]


@dataclass
class ThemeResult:
    themes: List[Theme]


THEME_FORMAT = """
Return JSON:
{
  "themes": [
    {
      "name": "...",
      "description": "...",
      "frequency": "high/medium/low or numeric",
      "representative_quotes": ["...", "..."]
    }
  ]
}
Provide between 3 and 6 themes.
"""


class ThemeExtractionAgent(AgentBase):
    def __init__(self) -> None:
        settings = get_settings()
        super().__init__(
            system_prompt=(
                "You are a qualitative coding specialist. Identify 3-6 concise themes, "
                "describe each, assign a frequency (high/medium/low or numeric), "
                "and attach short verbatim quotes to justify them. "
                "Always respond with JSON formatted like:\n"
                + THEME_FORMAT
            ),
            model=settings.models.reasoning,
        )

    def extract(self, transcript: str, *, rag_context: Optional[str] = None) -> ThemeResult:
        prompt_lines = [
            "Extract themes with quantitative-ish frequency cues and representative quotes.",
            "Transcript:",
            transcript,
        ]
        if rag_context:
            prompt_lines.extend(
                [
                    "",
                    "Historical context to compare against:",
                    rag_context,
                    "",
                    "Only reference this context when noting recurring patterns.",
                ]
            )
        payload = "\n".join(prompt_lines)
        response = self._run(payload)
        parsed = load_json_from_text(response_to_text(response))
        return ThemeResult(themes=[Theme(**theme) for theme in parsed["themes"]])
