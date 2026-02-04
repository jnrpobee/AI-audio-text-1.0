"""
Analyzes multiple transcripts together to surface shared themes and quotes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from .agents import SummaryAgent, TranscriptFormatterAgent
from .agents.collection import (
    CollectionQuoteAgent,
    CollectionSummaryAgent,
    CollectionThemeAgent,
)
from .rag.vector_store import InMemoryVectorStore, TranscriptDocument


@dataclass
class ParticipantAnalysis:
    participant_id: str
    source_path: str
    transcript: str
    summary_text: str
    similar_participants: List[tuple[str, float]] = field(default_factory=list)


@dataclass
class CollectionTheme:
    name: str
    description: str
    participants: List[str]
    supporting_quotes: List[Dict[str, str]]


@dataclass
class CollectionQuote:
    participant_id: str
    quote: str
    category: str
    insight: str


@dataclass
class CollectionAnalysisResult:
    participant_analyses: List[ParticipantAnalysis]
    overall_summary: str
    notable_patterns: List[str]
    themes: List[CollectionTheme]
    quotes: List[CollectionQuote]

    def participant_directory(self) -> List[tuple[str, str]]:
        return [(p.participant_id, p.source_path) for p in self.participant_analyses]

    def to_markdown(self) -> str:
        lines: List[str] = []
        lines.append("# Collection Analysis")
        lines.append("")
        lines.append("## Participant Directory")
        for pid, path in self.participant_directory():
            lines.append(f"- **{pid}** → `{path}`")
        lines.append("")
        lines.append("## Overall Summary")
        lines.append(self.overall_summary)
        if self.notable_patterns:
            lines.append("")
            lines.append("### Notable Patterns")
            for pattern in self.notable_patterns:
                lines.append(f"- {pattern}")
        lines.append("")
        lines.append("## Common Themes Across Interviews")
        for theme in self.themes:
            lines.append(f"### {theme.name}")
            lines.append(f"Participants: {', '.join(theme.participants)}")
            lines.append(theme.description)
            if theme.supporting_quotes:
                lines.append("Quotes:")
                for quote in theme.supporting_quotes:
                    participant = quote.get("participant_id", "unknown")
                    quote_text = quote.get("quote", "").strip()
                    source = quote.get("source_file", "n/a")
                    lines.append(f'- [{participant}] "{quote_text}" _(source: {source})_')
            lines.append("")
        lines.append("## Spotlight Quotes")
        for quote in self.quotes:
            lines.append(f'- **[{quote.participant_id}] ({quote.category.title()})** "{quote.quote}"')
            lines.append(f'  - Insight: {quote.insight}')
        return "\n".join(lines).strip()

    def save_markdown(self, path: str | Path) -> None:
        Path(path).write_text(self.to_markdown(), encoding="utf-8")

    def save_json(self, path: str | Path) -> None:
        payload = {
            "participant_directory": self.participant_directory(),
            "overall_summary": self.overall_summary,
            "notable_patterns": self.notable_patterns,
            "themes": [theme.__dict__ for theme in self.themes],
            "quotes": [quote.__dict__ for quote in self.quotes],
        }
        Path(path).write_text(
            json.dumps(payload, indent=2),  # type: ignore[name-defined]
            encoding="utf-8",
        )


class TranscriptCollectionAnalyzer:
    def __init__(self) -> None:
        self.formatter = TranscriptFormatterAgent()
        self.summary_agent = SummaryAgent()
        self.collection_summary_agent = CollectionSummaryAgent()
        self.collection_theme_agent = CollectionThemeAgent()
        self.collection_quote_agent = CollectionQuoteAgent()

    def _build_profiles(self, transcripts: Sequence[tuple[Path, str, Dict[str, str]]]) -> List[ParticipantAnalysis]:
        store = InMemoryVectorStore()
        profiles: List[ParticipantAnalysis] = []
        for idx, (path, text, _) in enumerate(transcripts):
            participant_id = f"P{idx+1}"
            formatted = self.formatter.format(text, mode="clean")
            summary = self.summary_agent.summarize(formatted)
            store.add(
                TranscriptDocument(
                    doc_id=participant_id,
                    text=formatted,
                    metadata={"source_path": str(path)},
                )
            )
            profiles.append(
                ParticipantAnalysis(
                    participant_id=participant_id,
                    source_path=str(path),
                    transcript=formatted,
                    summary_text=summary.short_summary,
                )
            )

        for profile in profiles:
            similar = store.most_similar(profile.transcript, top_k=4)
            sims: List[tuple[str, float]] = []
            for doc, score in similar:
                if doc.doc_id == profile.participant_id:
                    continue
                sims.append((doc.doc_id, score))
                if len(sims) == 2:
                    break
            profile.similar_participants = sims

        return profiles

    def _build_context(self, profiles: List[ParticipantAnalysis]) -> str:
        blocks: List[str] = []
        for profile in profiles:
            block_lines = [
                f"Participant: {profile.participant_id}",
                f"Source: {profile.source_path}",
                f"Summary: {profile.summary_text}",
            ]
            snippet = profile.transcript[:800].strip().replace("\n", " ")
            block_lines.append(f"Transcript Snippet: {snippet}")
            if profile.similar_participants:
                sims = ", ".join([f"{pid} ({score:.2f})" for pid, score in profile.similar_participants])
                block_lines.append(f"Similar Participants: {sims}")
            blocks.append("\n".join(block_lines))
        return "\n\n".join(blocks)

    def analyze(
        self,
        transcripts: Sequence[tuple[Path, str, Dict[str, str]]],
    ) -> CollectionAnalysisResult:
        if not transcripts:
            raise ValueError("No transcripts supplied for collection analysis.")

        profiles = self._build_profiles(transcripts)
        context = self._build_context(profiles)

        summary_payload = self.collection_summary_agent.summarize(context)
        theme_payload = self.collection_theme_agent.extract(context)
        quote_payload = self.collection_quote_agent.highlight(context)

        themes = [
            CollectionTheme(
                name=item.get("name", ""),
                description=item.get("description", ""),
                participants=item.get("participants", []),
                supporting_quotes=item.get("supporting_quotes", []),
            )
            for item in theme_payload.get("themes", [])
        ]
        quotes = [
            CollectionQuote(
                participant_id=item.get("participant_id", ""),
                quote=item.get("quote", ""),
                category=item.get("category", ""),
                insight=item.get("insight", ""),
            )
            for item in quote_payload.get("quotes", [])
        ]

        return CollectionAnalysisResult(
            participant_analyses=profiles,
            overall_summary=summary_payload.get("overall_summary", ""),
            notable_patterns=summary_payload.get("notable_patterns", []),
            themes=themes,
            quotes=quotes,
        )
