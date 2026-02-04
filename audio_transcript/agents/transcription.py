"""
Multimodal transcription agent that converts audio to clean text.
"""

from __future__ import annotations

from dataclasses import dataclass
import tempfile
from pathlib import Path
from typing import Any, Optional

from openai import BadRequestError, OpenAI

from ..config import get_openai_client, get_settings


MAX_CHUNK_SECONDS = 600  # keep comfortably below model's 1400s limit


@dataclass
class TranscriptionResult:
    transcript: str
    audio_format: str
    raw_transcript: Optional[str] = None
    verbatim_transcript: Optional[str] = None


class TranscriptionAgent:
    def __init__(
        self,
        *,
        client: Optional[OpenAI] = None,
        system_prompt: str | None = None,
        chunk_seconds: int = MAX_CHUNK_SECONDS,
    ) -> None:
        settings = get_settings()
        self.client = client or get_openai_client()
        self.model = settings.models.transcription
        self.system_prompt = system_prompt or (
            "You are a meticulous transcription agent. "
            "Transcribe every spoken detail exactly as heard, preserving wording, hesitations, and colloquialisms. "
            "Do not summarize or skip content; include pauses or noises only if they matter to meaning."
        )
        self.chunk_seconds = chunk_seconds

    def _transcribe_filelike(self, file_like, prompt: str) -> str:
        file_like.seek(0)
        response = self.client.audio.transcriptions.create(
            model=self.model,
            file=file_like,
            prompt=prompt,
        )
        return response.text.strip()

    def _load_audio(self, audio_path: Path) -> Any:
        try:
            from pydub import AudioSegment  # type: ignore
            from pydub.exceptions import CouldntDecodeError  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "Long-form transcription requires pydub. Install with `pip install pydub` "
                "and ensure FFmpeg is available on your PATH."
            ) from exc
        try:
            return AudioSegment.from_file(audio_path)
        except CouldntDecodeError as exc:
            raise RuntimeError(
                "Unable to decode audio file. Ensure FFmpeg is installed and the file is not corrupted."
            ) from exc

    @staticmethod
    def _should_chunk_from_error(exc: BadRequestError) -> bool:
        message = str(exc).lower()
        return "longer than" in message and "maximum" in message

    def _transcribe_long_audio(self, audio_path: Path, prompt: str) -> str:
        audio = self._load_audio(audio_path)
        chunk_ms = self.chunk_seconds * 1000
        segments = []
        total_segments = max(1, (len(audio) + chunk_ms - 1) // chunk_ms)
        for idx, start_ms in enumerate(range(0, len(audio), chunk_ms), start=1):
            chunk = audio[start_ms : start_ms + chunk_ms]
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_path = Path(temp_file.name)
            chunk.export(temp_path, format="wav")
            try:
                with temp_path.open("rb") as chunk_file:
                    chunk_prompt = (
                        f"{prompt}\n"
                        f"This is segment {idx}/{total_segments} of the same interview. "
                        "Continue the transcript seamlessly."
                    )
                    chunk_transcript = self._transcribe_filelike(chunk_file, chunk_prompt)
                    segments.append(f"[Segment {idx}] {chunk_transcript}")
            finally:
                if temp_path.exists():
                    temp_path.unlink(missing_ok=True)
        return "\n\n".join(segments)

    def transcribe(self, audio_path: str, *, context_hint: str | None = None) -> TranscriptionResult:
        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file does not exist: {audio_path}")
        audio_format = audio_path.suffix.replace(".", "").lower()
        prompt = context_hint or self.system_prompt

        try:
            with audio_path.open("rb") as audio_file:
                transcript = self._transcribe_filelike(audio_file, prompt)
        except BadRequestError as exc:
            if self._should_chunk_from_error(exc):
                transcript = self._transcribe_long_audio(audio_path, prompt)
            else:
                raise

        return TranscriptionResult(
            transcript=transcript,
            audio_format=audio_format,
            raw_transcript=transcript,
        )
