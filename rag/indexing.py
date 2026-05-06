import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import chromadb
import ollama


REQUIRED_CHUNK_FIELDS = ("chunk_id", "source_file", "text", "char_start", "char_end")


@dataclass
class IndexingFailure:
    chunk_ref: str
    reason: str


@dataclass
class IndexingResult:
    chunks_processed: int
    vectors_saved: int
    collection_count: int
    failures: list[IndexingFailure]

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunks_processed": self.chunks_processed,
            "vectors_saved": self.vectors_saved,
            "collection_count": self.collection_count,
            "failures": [
                {"chunk_ref": failure.chunk_ref, "reason": failure.reason} for failure in self.failures
            ],
        }


def _deterministic_id(source_file: str, chunk_id: str) -> str:
    key = f"{source_file}::{chunk_id}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def _embed_texts(texts: list[str], embedding_model: str) -> list[list[float]]:
    host = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    client = ollama.Client(host=host)

    # Keep compatibility across ollama client versions.
    if hasattr(client, "embed"):
        response = client.embed(model=embedding_model, input=texts)
        embeddings = response.get("embeddings")
        if not isinstance(embeddings, list):
            raise ValueError("Ollama embed response missing embeddings list.")
        return embeddings

    if hasattr(client, "embeddings"):
        embeddings: list[list[float]] = []
        for text in texts:
            response = client.embeddings(model=embedding_model, prompt=text)
            vector = response.get("embedding")
            if not isinstance(vector, list):
                raise ValueError("Ollama embeddings response missing embedding vector.")
            embeddings.append(vector)
        return embeddings

    raise RuntimeError("Unsupported ollama client version: no embed/embeddings API found.")


def _validate_chunk_record(record: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    chunk_ref = str(record.get("chunk_id", "<missing_chunk_id>"))
    missing = [field for field in REQUIRED_CHUNK_FIELDS if field not in record]
    if missing:
        return None, f"missing_fields:{','.join(missing)}"
    if not str(record["text"]).strip():
        return None, "empty_text"
    try:
        char_start = int(record["char_start"])
        char_end = int(record["char_end"])
    except (TypeError, ValueError):
        return None, "invalid_char_span"
    if char_end <= char_start:
        return None, "invalid_char_span_order"

    return (
        {
            "chunk_ref": chunk_ref,
            "chunk_id": str(record["chunk_id"]),
            "source_file": str(record["source_file"]),
            "text": str(record["text"]),
            "char_start": char_start,
            "char_end": char_end,
        },
        None,
    )


def index_chunks_to_chroma(
    chunks: list[dict[str, Any]],
    embedding_model: str,
    collection_name: str,
    persist_dir: Path,
    batch_size: int = 32,
) -> IndexingResult:
    if batch_size <= 0:
        raise ValueError("batch_size must be greater than 0")

    persist_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(persist_dir))
    collection = client.get_or_create_collection(name=collection_name)

    failures: list[IndexingFailure] = []
    valid_records: list[dict[str, Any]] = []

    for record in chunks:
        validated, reason = _validate_chunk_record(record)
        if reason:
            chunk_ref = str(record.get("chunk_id", "<missing_chunk_id>"))
            failures.append(IndexingFailure(chunk_ref=chunk_ref, reason=reason))
            continue
        valid_records.append(validated)

    vectors_saved = 0
    for start in range(0, len(valid_records), batch_size):
        batch = valid_records[start : start + batch_size]
        ids = [_deterministic_id(record["source_file"], record["chunk_id"]) for record in batch]
        documents = [record["text"] for record in batch]
        metadatas = [
            {
                "chunk_id": record["chunk_id"],
                "source_file": record["source_file"],
                "char_start": record["char_start"],
                "char_end": record["char_end"],
            }
            for record in batch
        ]

        try:
            embeddings = _embed_texts(documents, embedding_model=embedding_model)
            if len(embeddings) != len(batch):
                raise ValueError(
                    f"embeddings_count_mismatch expected={len(batch)} got={len(embeddings)}"
                )
            collection.upsert(ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas)
            vectors_saved += len(batch)
        except Exception as exc:  # noqa: BLE001
            for record in batch:
                failures.append(
                    IndexingFailure(chunk_ref=str(record["chunk_ref"]), reason=str(exc))
                )

    collection_count = collection.count()
    return IndexingResult(
        chunks_processed=len(chunks),
        vectors_saved=vectors_saved,
        collection_count=collection_count,
        failures=failures,
    )
