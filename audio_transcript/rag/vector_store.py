"""
Simple in-memory vector store for optional transcript RAG.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, List, Sequence

import numpy as np
from openai import OpenAI

from ..config import get_openai_client, get_settings
from ..utils import read_transcript_file


@dataclass
class TranscriptDocument:
    doc_id: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


class InMemoryVectorStore:
    """
    Lightweight cosine-similarity store backed by OpenAI embeddings.
    """

    def __init__(
        self,
        client: OpenAI | None = None,
        embedding_model: str | None = None,
    ) -> None:
        settings = get_settings()
        self.client = client or get_openai_client()
        self.embedding_model = embedding_model or settings.models.embedding
        self.documents: list[TranscriptDocument] = []
        self.embeddings: list[np.ndarray] = []

    def add(self, document: TranscriptDocument) -> None:
        embedding = self._embed(document.text)
        self.documents.append(document)
        self.embeddings.append(embedding)

    def _embed(self, text: str) -> np.ndarray:
        response = self.client.embeddings.create(
            model=self.embedding_model,
            input=text,
        )
        return np.array(response.data[0].embedding, dtype=np.float32)

    def most_similar(self, query: str, top_k: int | None = None) -> list[tuple[TranscriptDocument, float]]:
        if not self.documents:
            return []

        query_vec = self._embed(query)
        normalized_store = [vec / (np.linalg.norm(vec) + 1e-8) for vec in self.embeddings]
        normalized_query = query_vec / (np.linalg.norm(query_vec) + 1e-8)

        scores = [float(np.dot(normalized_query, vec)) for vec in normalized_store]
        ranked = sorted(zip(self.documents, scores), key=lambda pair: pair[1], reverse=True)
        return ranked[: top_k or get_settings().rag_top_k]

    def ingest_directory(self, directory: str | Path) -> None:
        directory = Path(directory)
        if not directory.exists():
            raise FileNotFoundError(f"RAG directory not found: {directory}")

        supported_suffixes = {".txt", ".md", ".json"}
        files = [path for path in directory.glob("**/*") if path.suffix.lower() in supported_suffixes]
        for path in files:
            text, metadata = self._load_file(path)
            self.add(
                TranscriptDocument(
                    doc_id=path.stem,
                    text=text,
                    metadata=metadata,
                )
            )

    @staticmethod
    def _load_file(path: Path) -> tuple[str, dict[str, Any]]:
        return read_transcript_file(path)

    def to_dict(self) -> dict[str, Any]:
        return {
            "embedding_model": self.embedding_model,
            "documents": [
                {"doc_id": doc.doc_id, "text": doc.text, "metadata": doc.metadata}
                for doc in self.documents
            ],
            "embeddings": [vec.tolist() for vec in self.embeddings],
        }

    def save_to_file(self, path: str | Path) -> None:
        payload = self.to_dict()
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def load_from_file(self, path: str | Path) -> None:
        path = Path(path)
        if not path.exists():
            return
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("embedding_model") and payload["embedding_model"] != self.embedding_model:
            raise ValueError(
                f"Stored embedding model {payload['embedding_model']} does not match current {self.embedding_model}"
            )
        docs = payload.get("documents", [])
        embeddings = payload.get("embeddings", [])
        if len(docs) != len(embeddings):
            raise ValueError("Mismatch between stored documents and embeddings.")
        for info, emb in zip(docs, embeddings):
            document = TranscriptDocument(
                doc_id=info["doc_id"],
                text=info["text"],
                metadata=info.get("metadata", {}),
            )
            self.documents.append(document)
            self.embeddings.append(np.array(emb, dtype=np.float32))
