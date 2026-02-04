"""
Misc helpers shared across agents.
"""

from __future__ import annotations

import base64
import json
import re
from pathlib import Path
from typing import Any, Tuple


def encode_audio_file(path: str | Path) -> tuple[str, str]:
    """
    Returns (base64_data, audio_format) for the given file path.
    """

    audio_path = Path(path)
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")
    audio_format = audio_path.suffix.replace(".", "").lower()
    if not audio_format:
        raise ValueError("Audio format could not be inferred from file extension.")
    data = audio_path.read_bytes()
    encoded = base64.b64encode(data).decode("utf-8")
    return encoded, audio_format


def response_to_text(response: Any) -> str:
    """
    Normalizes OpenAI response objects to plain text.
    """

    if hasattr(response, "output_text"):
        return response.output_text
    if hasattr(response, "choices"):
        return response.choices[0].message.content  # type: ignore[return-value]
    raise ValueError("Unable to parse response text from OpenAI result.")


def load_json_from_text(raw_text: str) -> Any:
    """
    Attempts to parse JSON, tolerating fenced code blocks or stray commentary.
    """

    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned, count=1, flags=re.IGNORECASE).strip()
        if cleaned.endswith("```"):
            cleaned = cleaned[: -3].rstrip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        preview = cleaned[:200].replace("\n", " ")
        raise ValueError(f"Unable to parse JSON from model response: {preview}") from None


def read_transcript_file(path: str | Path) -> Tuple[str, dict[str, Any]]:
    """
    Loads transcript text (txt/md/json) plus any metadata.
    """

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Transcript file not found: {path}")

    metadata: dict[str, Any] = {}
    suffix = path.suffix.lower()
    if suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            transcript = data.get("transcript") or data.get("text") or json.dumps(data)
            metadata = {k: v for k, v in data.items() if k not in {"transcript", "text"}}
        else:
            transcript = json.dumps(data)
    elif suffix == ".docx":
        try:
            import docx  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "python-docx is required to read .docx transcripts. Install it via `pip install python-docx`."
            ) from exc
        document = docx.Document(str(path))
        transcript = "\n".join(paragraph.text for paragraph in document.paragraphs)
    elif suffix == ".pdf":
        try:
            from pypdf import PdfReader  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "pypdf is required to read .pdf transcripts. Install it via `pip install pypdf`."
            ) from exc
        reader = PdfReader(str(path))
        transcript = "\n".join((page.extract_text() or "") for page in reader.pages)
    else:
        transcript = path.read_text(encoding="utf-8")
    metadata.setdefault("source_path", str(path))
    metadata.setdefault("source_type", suffix.lstrip(".") or "text")
    return transcript, metadata
