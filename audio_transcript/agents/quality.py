"""
Quality assurance agent that reviews analysis output.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from .base import AgentBase
from ..utils import load_json_from_text, response_to_text


@dataclass
class QualityReview:
    status: str
    severity: str
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    @property
    def needs_revision(self) -> bool:
        return self.status.lower() != "pass" and bool(self.recommendations)


QUALITY_FORMAT = """
Respond with valid JSON shaped like:
{
  "status": "pass" | "needs_revision",
  "severity": "none" | "low" | "medium" | "high",
  "issues": ["description", "..."],
  "recommendations": ["actionable improvement", "..."]
}
"""


class QualityReviewAgent(AgentBase):
    def __init__(self) -> None:
        super().__init__(
            system_prompt=(
                "You are the QA agent for an interview-analysis pipeline. "
                "Inspect the structured results plus their markdown rendering. "
                "Flag factual inconsistencies, missing sections, JSON compliance issues, "
                "or any unclear writing. "
                "Only output JSON using this schema:\n"
                + QUALITY_FORMAT
            ),
            temperature=0.2,
        )

    def review(self, analysis_json: str, markdown: str) -> QualityReview:
        prompt = "\n".join(
            [
                "Evaluate the following analysis output.",
                "",
                "Structured JSON:",
                analysis_json,
                "",
                "Rendered Markdown:",
                markdown,
            ]
        )
        response = self._run(prompt)
        data = load_json_from_text(response_to_text(response))
        return QualityReview(
            status=data.get("status", "pass"),
            severity=data.get("severity", "none"),
            issues=data.get("issues", []) or [],
            recommendations=data.get("recommendations", []) or [],
        )
