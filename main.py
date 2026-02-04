from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List, Optional

from audio_transcript.config import get_settings  # noqa: F401  # ensures .env loading
from audio_transcript.pipeline import InterviewAnalysisPipeline, InterviewAnalysisResult
from audio_transcript.rag.vector_store import InMemoryVectorStore
from audio_transcript.utils import read_transcript_file
from audio_transcript.collection_analyzer import TranscriptCollectionAnalyzer


def parse_metadata(items: Optional[list[str]]) -> Dict[str, str]:
    result: Dict[str, str] = {}
    if not items:
        return result
    for item in items:
        if "=" not in item:
            raise ValueError(f"Metadata must use key=value form. Got: {item}")
        key, value = item.split("=", 1)
        result[key.strip()] = value.strip()
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Multi-modal audio + text interview analyzer."
    )
    parser.add_argument("--audio", help="Path to the interview audio file.")
    parser.add_argument(
        "--metadata",
        nargs="*",
        help="Optional metadata entries as key=value pairs.",
    )
    parser.add_argument("--out-md", help="Optional path to save a Markdown report.")
    parser.add_argument("--out-json", help="Optional path to save the structured JSON.")
    parser.add_argument(
        "--enable-rag",
        action="store_true",
        help="Enable retrieval augmented context from past transcripts.",
    )
    parser.add_argument(
        "--rag-dir",
        help="Directory containing previous transcripts (.txt/.md/.json) to ingest.",
    )
    parser.add_argument(
        "--context-hint",
        help="Short hint passed to the transcription model (e.g., domain, participant).",
    )
    parser.add_argument(
        "--rag-top-k",
        type=int,
        default=3,
        help="How many similar transcripts to surface when RAG is enabled.",
    )
    parser.add_argument(
        "--transcript-dir",
        default="reports/transcripts",
        help="Directory where raw + formatted transcript text files are stored.",
    )
    parser.add_argument(
        "--quality-report-dir",
        default="reports/quality",
        help="Directory where quality and reasoning reports are stored.",
    )
    parser.add_argument(
        "--rag-store-file",
        help="Optional path to persist embeddings for previous transcripts (JSON).",
    )
    parser.add_argument(
        "--transcript",
        action="append",
        dest="transcripts",
        help="Path to a transcript (.txt/.md/.json) to analyze without audio. Repeat to process multiple files.",
    )
    parser.add_argument(
        "--transcript-dir-only",
        help="Directory containing transcript files (txt/md/json) to analyze without audio.",
    )
    parser.add_argument(
        "--report-dir",
        default="reports",
        help="Directory used when automatically naming markdown outputs (transcript-only mode or when --out-md is omitted).",
    )
    parser.add_argument(
        "--aggregate-transcripts",
        action="store_true",
        help="When analyzing multiple transcripts, also produce a single combined report that captures cross-interview insights.",
    )
    parser.add_argument(
        "--aggregate-name",
        default="combined",
        help="Filename stem for the aggregated transcript report (default: combined).",
    )
    parser.add_argument(
        "--aggregate-only",
        action="store_true",
        help="When aggregating transcripts, skip per-file reports and only generate the combined analysis.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    metadata = parse_metadata(args.metadata)
    rag_store = None
    if args.rag_store_file:
        rag_store = InMemoryVectorStore()
        rag_store.load_from_file(args.rag_store_file)

    pipeline = InterviewAnalysisPipeline(rag_store=rag_store)
    collection_analyzer = TranscriptCollectionAnalyzer()

    transcript_files: list[Path] = []
    if args.transcripts:
        transcript_files.extend(Path(path) for path in args.transcripts)
    if args.transcript_dir_only:
        base_dir = Path(args.transcript_dir_only)
        if not base_dir.exists():
            parser.error(f"Transcript directory not found: {base_dir}")
        supported_suffixes = {".txt", ".md", ".json", ".docx", ".pdf"}
        transcript_files.extend([path for path in base_dir.glob("**/*") if path.suffix.lower() in supported_suffixes])

    if not args.audio and not transcript_files:
        parser.error("Provide --audio or at least one --transcript/--transcript-dir-only input.")

    loaded_transcripts: List[tuple[Path, str, Dict[str, str]]] = []
    for transcript_path in transcript_files:
        transcript_text, file_meta = read_transcript_file(transcript_path)
        loaded_transcripts.append((transcript_path, transcript_text, file_meta))

    def save_full_reports(result: InterviewAnalysisResult, base_name: str, explicit_path: Optional[Path]) -> None:
        if explicit_path is None:
            reports_dir = Path(args.report_dir) / "general"
            reports_dir.mkdir(parents=True, exist_ok=True)
            explicit_path = reports_dir / f"{base_name}.md"
        explicit_path.parent.mkdir(parents=True, exist_ok=True)
        result.save_markdown(explicit_path)

        clean_dir = explicit_path.parent / "clean"
        original_dir = explicit_path.parent / "original"
        clean_dir.mkdir(parents=True, exist_ok=True)
        original_dir.mkdir(parents=True, exist_ok=True)
        result.save_markdown(clean_dir / explicit_path.name, transcript_variant="clean")
        result.save_markdown(
            original_dir / explicit_path.name,
            transcript_variant="original",
            use_corrected=False,
        )

        transcripts_dir = Path(args.transcript_dir)
        transcripts_dir.mkdir(parents=True, exist_ok=True)
        result.save_transcripts(transcripts_dir, base_name=base_name)

        if args.quality_report_dir:
            result.save_quality_report(args.quality_report_dir, base_name=base_name)

    output_consumed = False

    if args.audio:
        result = pipeline.run(
            audio_path=args.audio,
            metadata=metadata,
            rag_enabled=args.enable_rag,
            rag_directory=args.rag_dir,
            rag_top_k=args.rag_top_k,
            context_hint=args.context_hint,
        )

        if args.out_md:
            save_full_reports(result, Path(args.out_md).stem, Path(args.out_md))
            output_consumed = True
        if args.out_json:
            Path(args.out_json).parent.mkdir(parents=True, exist_ok=True)
            result.save_json(args.out_json)
            output_consumed = True
        if not args.out_md:
            base_name = Path(args.audio).stem
            save_full_reports(result, base_name, None)
            output_consumed = True

    if not args.aggregate_only:
        for idx, (transcript_path, transcript_text, file_meta) in enumerate(loaded_transcripts, start=1):
            combined_metadata = {**file_meta, **metadata}
            result = pipeline.run_with_transcript_text(
                transcript_text,
                metadata=combined_metadata,
                rag_enabled=args.enable_rag,
                rag_directory=args.rag_dir,
                rag_top_k=args.rag_top_k,
            )
            base_name = transcript_path.stem
            explicit_path = None
            if args.out_md and not args.audio and len(loaded_transcripts) == 1:
                explicit_path = Path(args.out_md)
            save_full_reports(result, base_name, explicit_path)
            if args.out_json:
                json_path = Path(args.out_json) if len(loaded_transcripts) == 1 else Path(args.report_dir) / f"{base_name}.json"
                json_path.parent.mkdir(parents=True, exist_ok=True)
                result.save_json(json_path)
            output_consumed = True

    if args.aggregate_transcripts and loaded_transcripts:
        collection_result = collection_analyzer.analyze(loaded_transcripts)
        base_name = args.aggregate_name or "combined"
        aggregate_dir = Path(args.report_dir) / "general"
        aggregate_dir.mkdir(parents=True, exist_ok=True)
        aggregate_path = aggregate_dir / f"{base_name}.md"
        collection_result.save_markdown(aggregate_path)
        if args.out_json:
            json_path = aggregate_dir / f"{base_name}.json"
            collection_result.save_json(json_path)
        output_consumed = True

    if args.rag_store_file and pipeline.rag_store:
        pipeline.rag_store.save_to_file(args.rag_store_file)

    if not output_consumed:
        print(result.to_markdown())


if __name__ == "__main__":
    main()
