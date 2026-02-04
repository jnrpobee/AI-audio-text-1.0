"""
Agent that generates follow-up interview questions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from ..config import get_settings
from ..utils import load_json_from_text, response_to_text
from .base import AgentBase


@dataclass
class FollowUpQuestions:
    clarifying: List[str]
    probing: List[str]
    contrast: List[str]


FOLLOWUP_FORMAT = """
Return JSON:
{
  "clarifying": ["...", "..."],
  "probing": ["...", "..."],
  "contrast": ["...", "..."]
}
Each list must contain at least two targeted questions.
"""


class FollowUpQuestionAgent(AgentBase):
    def __init__(self) -> None:
        settings = get_settings()
        super().__init__(
            system_prompt=(
                "You design follow-up interview questions that build on prior content. "
                "Focus on clarifying ambiguous responses, probing deeper into motivations, "
                "and prompting comparison or contrast where useful. "
                "Return JSON formatted as:\n"
                + FOLLOWUP_FORMAT
            ),
            model=settings.models.reasoning,
        )

    def generate(self, transcript: str) -> FollowUpQuestions:
        prompt = "\n".join(
            [
                "Generate targeted follow-up questions in three styles: clarifying, probing, contrast/compare.",
                "Pull directly from transcript cues so interviewers can reference specifics.",
                "",
                "Transcript:",
                transcript,
            ]
        )
        response = self._run(prompt)
        parsed = load_json_from_text(response_to_text(response))
        return FollowUpQuestions(**parsed)
