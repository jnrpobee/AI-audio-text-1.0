"""
High-level orchestration for the multi-agent interview analyzer.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Optional

from .agents import (
    CorrectionAgent,
    CorrectionResult,
    FollowUpQuestionAgent,
    FollowUpQuestions,
    QuoteHighlighterAgent,
    QuoteHighlights,
    QualityReviewAgent,
    QualityReview,
    SummaryAgent,
    SummaryResult,
    ThemeExtractionAgent,
    ThemeResult,
    TranscriptFormatterAgent,
    TranscriptionAgent,
    TranscriptionResult,
)
from .rag.vector_store import InMemoryVectorStore


@dataclass
class InterviewAnalysisResult:
    transcription: TranscriptionResult
    summary: SummaryResult
    themes: ThemeResult
    quotes: QuoteHighlights
    follow_ups: FollowUpQuestions
    rag_context: Optional[str] = None
    metadata: Dict[str, str] | None = None
    quality_review: Optional[QualityReview] = None
    correction: Optional[CorrectionResult] = None

    def _base_markdown(self, transcript_variant: str = "clean") -> str:
        if transcript_variant == "original":
            transcript_text = (
                self.transcription.verbatim_transcript
                or self.transcription.raw_transcript
                or self.transcription.transcript
            )
        else:
            transcript_text = self.transcription.transcript

        lines = [
            "# Interview Analysis",
            "",
            "## Transcript",
            transcript_text,
            "",
            "## Summary",
            f"**Short:** {self.summary.short_summary}",
            "",
            f"**Long:** {self.summary.long_summary}",
            "",
            "## Themes",
        ]
        for idx, theme in enumerate(self.themes.themes, start=1):
            quotes_block = "\n".join([f'    - "{q}"' for q in theme.representative_quotes])
            lines.extend(
                [
                    f"{idx}. **{theme.name}** ({theme.frequency}) — {theme.description}",
                    quotes_block,
                    "",
                ]
            )
        lines.append("## Quote Highlights")
        for highlight in self.quotes.highlights:
            lines.extend(
                [
                    f"- **{highlight.category.title()}**: \"{highlight.quote}\"",
                    f"  - Rationale: {highlight.rationale}",
                    f"  - Suggested Use: {highlight.suggested_use}",
                ]
            )
        lines.append("")
        lines.append("## Follow-up Questions")
        lines.append("### Clarifying")
        lines.extend([f"- {q}" for q in self.follow_ups.clarifying])
        lines.append("### Probing")
        lines.extend([f"- {q}" for q in self.follow_ups.probing])
        lines.append("### Contrast / Compare")
        lines.extend([f"- {q}" for q in self.follow_ups.contrast])
        if self.rag_context:
            lines.extend(["", "## Contextual Similarities", self.rag_context])
        if self.metadata:
            lines.extend(
                [
                    "",
                    "## Metadata",
                ]
                + [f"- {key}: {value}" for key, value in self.metadata.items()]
            )
        return "\n".join(lines)

    def _markdown_with_quality(self, base_markdown: str) -> str:
        lines = [base_markdown]
        if self.quality_review:
            lines.extend(
                [
                    "",
                    "## Quality Review",
                    f"- Status: {self.quality_review.status}",
                    f"- Severity: {self.quality_review.severity}",
                ]
            )
            if self.quality_review.issues:
                lines.append("- Issues:")
                lines.extend([f"  - {issue}" for issue in self.quality_review.issues])
        if self.correction and self.correction.change_log:
            lines.extend(
                [
                    "",
                    "## Correction Change Log",
                ]
                + [f"- {entry}" for entry in self.correction.change_log]
            )
        return "\n".join(lines)

    def to_markdown(self, use_corrected: bool = True, transcript_variant: str = "clean") -> str:
        base_with_quality = self._markdown_with_quality(self._base_markdown(transcript_variant))
        if transcript_variant == "clean":
            if (
                use_corrected
                and self.correction
                and self.correction.applied
                and self.correction.updated_markdown
            ):
                return self.correction.updated_markdown
        return base_with_quality

    def _as_serializable(self) -> Dict[str, object]:
        serializable = asdict(self)
        serializable["transcription"] = asdict(self.transcription)
        serializable["summary"] = asdict(self.summary)
        serializable["themes"] = {"themes": [asdict(theme) for theme in self.themes.themes]}
        serializable["quotes"] = {
            "highlights": [asdict(highlight) for highlight in self.quotes.highlights]
        }
        serializable["follow_ups"] = asdict(self.follow_ups)
        if self.quality_review:
            serializable["quality_review"] = asdict(self.quality_review)
        if self.correction:
            serializable["correction"] = asdict(self.correction)
        return serializable

    def to_json(self) -> str:
        serializable = self._as_serializable()
        return json.dumps(serializable, indent=2)

    def save_markdown(
        self, path: str | Path, *, use_corrected: bool = True, transcript_variant: str = "clean"
    ) -> None:
        Path(path).write_text(
            self.to_markdown(use_corrected=use_corrected, transcript_variant=transcript_variant),
            encoding="utf-8",
        )

    def save_json(self, path: str | Path) -> None:
        Path(path).write_text(self.to_json(), encoding="utf-8")

    def save_transcripts(self, directory: str | Path, *, base_name: str | None = None) -> None:
        directory = Path(directory)
        base = base_name or "transcript"

        clean_dir = directory / "clean"
        clean_dir.mkdir(parents=True, exist_ok=True)
        clean_path = clean_dir / f"{base}_clean.txt"
        clean_path.write_text(self.transcription.transcript, encoding="utf-8")

        verbatim_source = self.transcription.verbatim_transcript or self.transcription.raw_transcript
        if verbatim_source:
            verbatim_dir = directory / "verbatim"
            verbatim_dir.mkdir(parents=True, exist_ok=True)
            verbatim_path = verbatim_dir / f"{base}_verbatim.txt"
            verbatim_path.write_text(verbatim_source, encoding="utf-8")

    def save_quality_report(self, directory: str | Path, *, base_name: str | None = None) -> None:
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        base = base_name or "quality"
        report_path = directory / f"{base}_quality.md"

        if not self.quality_review:
            report_path.write_text("No quality review available for this run.", encoding="utf-8")
            return

        lines = [
            "# Quality & Reasoning Report",
            "",
            f"- Status: {self.quality_review.status}",
            f"- Severity: {self.quality_review.severity}",
        ]
        if self.quality_review.issues:
            lines.append("## Issues")
            lines.extend([f"- {issue}" for issue in self.quality_review.issues])
        if self.quality_review.recommendations:
            lines.append("## Recommendations")
            lines.extend([f"- {rec}" for rec in self.quality_review.recommendations])
        if self.correction:
            lines.append("## Correction Summary")
            lines.append(f"- Applied: {'Yes' if self.correction.applied else 'No'}")
            if self.correction.change_log:
                lines.append("### Change Log")
                lines.extend([f"- {entry}" for entry in self.correction.change_log])
        report_path.write_text("\n".join(lines), encoding="utf-8")


class InterviewAnalysisPipeline:
    def __init__(
        self,
        *,
        rag_store: Optional[InMemoryVectorStore] = None,
        auto_ingest_rag_dir: str | None = None,
    ) -> None:
        self.transcription_agent = TranscriptionAgent()
        self.summary_agent = SummaryAgent()
        self.theme_agent = ThemeExtractionAgent()
        self.quote_agent = QuoteHighlighterAgent()
        self.follow_up_agent = FollowUpQuestionAgent()
        self.transcript_formatter = TranscriptFormatterAgent()
        self.quality_agent = QualityReviewAgent()
        self.correction_agent = CorrectionAgent()
        self.rag_store = rag_store or InMemoryVectorStore()
        if auto_ingest_rag_dir:
            self.rag_store.ingest_directory(auto_ingest_rag_dir)

    def _format_rag_context(self, transcript: str, top_k: int) -> str:
        similar = self.rag_store.most_similar(transcript, top_k=top_k)
        if not similar:
            return ""
        blocks = []
        for doc, score in similar:
            preview = doc.text[:400].replace("\n", " ")
            blocks.append(
                f"- {doc.doc_id} (score={score:.2f}): {preview}..."
            )
        return "\n".join(blocks)

    def _format_transcription(self, transcription: TranscriptionResult) -> TranscriptionResult:
        raw_transcript = transcription.raw_transcript or transcription.transcript
        transcription.raw_transcript = raw_transcript
        transcription.verbatim_transcript = self.transcript_formatter.format(
            raw_transcript, mode="verbatim"
        )
        transcription.transcript = self.transcript_formatter.format(raw_transcript, mode="clean")
        return transcription

    def _analyze_transcription(
        self,
        transcription: TranscriptionResult,
        *,
        metadata: Optional[Dict[str, str]] = None,
        rag_top_k: int = 3,
        rag_enabled: bool = False,
        rag_directory: str | None = None,
    ) -> InterviewAnalysisResult:
        if rag_directory:
            self.rag_store.ingest_directory(rag_directory)

        rag_context = ""
        if rag_enabled:
            rag_context = self._format_rag_context(transcription.transcript, top_k=rag_top_k)

        summary = self.summary_agent.summarize(
            transcription.transcript, rag_context=rag_context or None
        )
        themes = self.theme_agent.extract(
            transcription.transcript, rag_context=rag_context or None
        )
        quotes = self.quote_agent.highlight(transcription.transcript)
        follow_ups = self.follow_up_agent.generate(transcription.transcript)

        result = InterviewAnalysisResult(
            transcription=transcription,
            summary=summary,
            themes=themes,
            quotes=quotes,
            follow_ups=follow_ups,
            rag_context=rag_context or None,
            metadata=metadata,
        )

        base_markdown = result._base_markdown("clean")
        analysis_json = json.dumps(result._as_serializable(), indent=2)
        quality_review = self.quality_agent.review(analysis_json, base_markdown)
        result.quality_review = quality_review

        if quality_review.needs_revision:
            quality_json = json.dumps(
                {
                    "status": quality_review.status,
                    "severity": quality_review.severity,
                    "issues": quality_review.issues,
                    "recommendations": quality_review.recommendations,
                },
                indent=2,
            )
            correction = self.correction_agent.apply(base_markdown, quality_json)
            result.correction = correction
        else:
            result.correction = None

        return result

    def run(
        self,
        audio_path: str,
        *,
        metadata: Optional[Dict[str, str]] = None,
        rag_top_k: int = 3,
        rag_enabled: bool = False,
        rag_directory: str | None = None,
        context_hint: str | None = None,
    ) -> InterviewAnalysisResult:
        transcription = self.transcription_agent.transcribe(
            audio_path, context_hint=context_hint
        )
        transcription = self._format_transcription(transcription)
        return self._analyze_transcription(
            transcription,
            metadata=metadata,
            rag_top_k=rag_top_k,
            rag_enabled=rag_enabled,
            rag_directory=rag_directory,
        )

    def run_with_transcript_text(
        self,
        transcript_text: str,
        *,
        metadata: Optional[Dict[str, str]] = None,
        rag_top_k: int = 3,
        rag_enabled: bool = False,
        rag_directory: str | None = None,
    ) -> InterviewAnalysisResult:
        transcription = TranscriptionResult(
            transcript=transcript_text,
            audio_format="text",
            raw_transcript=transcript_text,
        )
        transcription = self._format_transcription(transcription)
        return self._analyze_transcription(
            transcription,
            metadata=metadata,
            rag_top_k=rag_top_k,
            rag_enabled=rag_enabled,
            rag_directory=rag_directory,
        )
