"""
Agent that applies quality review recommendations to the markdown report.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from .base import AgentBase
from ..utils import load_json_from_text, response_to_text


@dataclass
class CorrectionResult:
    applied: bool
    change_log: List[str] = field(default_factory=list)
    updated_markdown: str = ""


CORRECTION_FORMAT = """
Respond with JSON:
{
  "applied": true | false,
  "change_log": ["summary of adjustment", "..."],
  "updated_markdown": "full markdown document after fixes (string)"
}
"""


class CorrectionAgent(AgentBase):
    def __init__(self) -> None:
        super().__init__(
            system_prompt=(
                "You are a corrective agent. Given the original markdown report and QA findings, "
                "apply only the necessary fixes while preserving the document structure "
                "(headings, lists, etc.). "
                "Explicitly mention adjustments in a change log. "
                "Always return JSON using:\n"
                + CORRECTION_FORMAT
            ),
            temperature=0.3,
        )

    def apply(self, original_markdown: str, quality_review_json: str) -> CorrectionResult:
        prompt = "\n".join(
            [
                "Original Markdown Report:",
                original_markdown,
                "",
                "Quality Review Findings:",
                quality_review_json,
            ]
        )
        response = self._run(prompt)
        data = load_json_from_text(response_to_text(response))
        return CorrectionResult(
            applied=bool(data.get("applied", False)),
            change_log=data.get("change_log", []) or [],
            updated_markdown=data.get("updated_markdown", original_markdown),
        )
