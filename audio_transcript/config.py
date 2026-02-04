"""
Shared configuration and OpenAI client helpers.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field

# Load environment variables from root and env/.env if present.
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv()
load_dotenv(BASE_DIR / ".env")
load_dotenv(BASE_DIR / "env" / ".env")

# this is the model settings for the pipeline, which includes the transcription, reasoning, and embedding models.
# the transcription model is used to transcribe the audio into text.
# the reasoning model is used to reason about the text and generate the summary, themes, and quotes.
# the embedding model is used to embed the text into a vector space for RAG.
class ModelSettings(BaseModel):
    """Model names grouped in one place for quick tweaks."""

    transcription: str = Field(
        default="gpt-4o-mini-transcribe-2025-12-15",
        description="Used by the multimodal transcription agent.",
    )
    reasoning: str = Field(
        default="gpt-5.2",
        description="Used for downstream reasoning (summary, themes, etc.).",
    )
    embedding: str = Field(
        default="text-embedding-3-large",
        description="Used for RAG vectorization of previous interviews.",
    )


class Settings(BaseModel):
    """Runtime configuration for the interview analysis pipeline."""

    openai_api_key: str = Field(
        default_factory=lambda: os.getenv("OPENAI_API_KEY", ""),
        description="API key pulled from environment or .env file.",
    )
    default_temperature: float = Field(
        default=0.4, description="Temperature for reasoning agents."
    )
    rag_top_k: int = Field(
        default=3, description="How many similar transcripts to retrieve for context."
    )
    models: ModelSettings = Field(default_factory=ModelSettings)

    def ensure_api_key(self) -> str:
        if not self.openai_api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Export it or define it in a .env file."
            )
        return self.openai_api_key


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


@lru_cache(maxsize=1)
def get_openai_client(api_key: Optional[str] = None) -> OpenAI:
    """
    Returns a cached OpenAI client. Cache keeps our agents light-weight.
    """

    key = api_key or get_settings().ensure_api_key()
    return OpenAI(api_key=key)
