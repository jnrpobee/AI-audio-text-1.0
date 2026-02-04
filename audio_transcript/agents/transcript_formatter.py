"""
Agent that formats transcripts with clear speaker labeling and anonymization.
"""

from __future__ import annotations

from .base import AgentBase

CLEAN_PROMPT = """
Rewrite the interview transcript into a readable summary transcript.
- Label every turn explicitly as either "Interviewer:" or "Participant:".
- Ensure participants remain anonymous: replace any personal names or identifiers with "Participant" (or "Participant 1/2" for multiple speakers).
- Remove obvious filler words or repeated hesitations when they add no meaning, but keep the speaker's intent, tone, and nuance intact.
- Preserve chronological order and only omit sounds/notes that truly add no value.
- If interviewer identity is unclear, infer from context (questions vs answers) but keep the remaining content faithful to what was said.
Important: Output plain text formatted as alternating lines beginning with the speaker label. Do not add commentary outside of the transcript.
"""

VERBATIM_PROMPT = """
Rewrite the interview transcript so it remains completely verbatim yet clearly labeled.
- Label every turn explicitly as either "Interviewer:" or "Participant:".
- Ensure participants remain anonymous using "Participant" labels (add numbering only if multiple participants exist).
- Preserve every word, hesitation, filler, and nuance exactly as it appears; do NOT remove or summarize anything.
- Maintain chronological order and include non-verbal notes or timestamps only if present in the source.
Important: Output plain text with each line starting with the speaker label. No added commentary.
"""


class TranscriptFormatterAgent(AgentBase):
    def __init__(self) -> None:
        super().__init__(
            system_prompt=(
                "You are a transcript formatting agent for qualitative interviews. "
                "Your job is to produce both a clean version (minimal filler) and a verbatim version "
                "with clear speaker labels and anonymous participants."
            ),
            temperature=0.2,
        )

    def format(self, raw_transcript: str, mode: str = "clean") -> str:
        prompt_template = CLEAN_PROMPT if mode == "clean" else VERBATIM_PROMPT
        prompt = "\n".join(
            [
                prompt_template.strip(),
                "",
                "Raw transcript:",
                raw_transcript,
            ]
        )
        return self._run_and_parse_text(prompt).strip()
