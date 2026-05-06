import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


@dataclass
class RetrievedChunk:
    chunk_id: str
    source_file: str
    text: str
    char_start: int | None
    char_end: int | None
    distance: float | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "source_file": self.source_file,
            "text": self.text,
            "char_start": self.char_start,
            "char_end": self.char_end,
            "distance": self.distance,
        }


@dataclass
class RetrievalResult:
    question: str
    requested_top_k: int
    retrieval_time_ms: float
    chunks: list[RetrievedChunk]

    def to_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "requested_top_k": self.requested_top_k,
            "returned_chunks": len(self.chunks),
            "retrieval_time_ms": round(self.retrieval_time_ms, 3),
            "chunks": [chunk.to_dict() for chunk in self.chunks],
        }


def _log(message: str, log_fn: Callable[[str], None] | None) -> None:
    if log_fn is None:
        return
    log_fn(f"[retrieval] {message}")


def _create_ollama_client(host: str) -> Any:
    import ollama

    return ollama.Client(host=host)


def _chromadb_module() -> Any:
    import chromadb

    return chromadb


def _embed_query(question: str, embedding_model: str) -> list[float]:
    host = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    client = _create_ollama_client(host=host)

    # Keep compatibility across ollama client versions.
    if hasattr(client, "embed"):
        response = client.embed(model=embedding_model, input=question)
        embeddings = response.get("embeddings")
        if isinstance(embeddings, list) and embeddings:
            first_vector = embeddings[0]
            if isinstance(first_vector, list):
                return first_vector
        raise ValueError("Ollama embed response missing query vector.")

    if hasattr(client, "embeddings"):
        response = client.embeddings(model=embedding_model, prompt=question)
        vector = response.get("embedding")
        if isinstance(vector, list):
            return vector
        raise ValueError("Ollama embeddings response missing query vector.")

    raise RuntimeError("Unsupported ollama client version: no embed/embeddings API found.")


def _first_result_row(payload: dict[str, Any], key: str) -> list[Any]:
    values = payload.get(key)
    if not isinstance(values, list) or not values:
        return []
    first = values[0]
    if not isinstance(first, list):
        return []
    return first


def retrieve_similar_chunks(
    question: str,
    top_k: int,
    collection_name: str,
    persist_dir: Path,
    embedding_model: str,
    log_fn: Callable[[str], None] | None = print,
) -> RetrievalResult:
    if top_k <= 0:
        raise ValueError("top_k must be greater than 0")
    if not question.strip():
        raise ValueError("question must not be empty")

    start = time.perf_counter()

    chromadb = _chromadb_module()
    client = chromadb.PersistentClient(path=str(persist_dir))
    try:
        collection = client.get_collection(name=collection_name)
    except Exception:  # noqa: BLE001
        collection = None

    if collection is None:
        elapsed_ms = (time.perf_counter() - start) * 1000
        _log(
            (
                f"collection={collection_name} requested_top_k={top_k} "
                f"returned_chunks=0 retrieval_time_ms={elapsed_ms:.3f}"
            ),
            log_fn,
        )
        return RetrievalResult(
            question=question,
            requested_top_k=top_k,
            retrieval_time_ms=elapsed_ms,
            chunks=[],
        )

    if collection.count() == 0:
        elapsed_ms = (time.perf_counter() - start) * 1000
        _log(
            (
                f"collection={collection_name} requested_top_k={top_k} "
                f"returned_chunks=0 retrieval_time_ms={elapsed_ms:.3f}"
            ),
            log_fn,
        )
        return RetrievalResult(
            question=question,
            requested_top_k=top_k,
            retrieval_time_ms=elapsed_ms,
            chunks=[],
        )

    query_vector = _embed_query(question=question, embedding_model=embedding_model)
    query_result = collection.query(
        query_embeddings=[query_vector],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    documents = _first_result_row(query_result, "documents")
    metadatas = _first_result_row(query_result, "metadatas")
    distances = _first_result_row(query_result, "distances")

    chunks: list[RetrievedChunk] = []
    for idx, document in enumerate(documents):
        metadata = metadatas[idx] if idx < len(metadatas) and isinstance(metadatas[idx], dict) else {}
        distance = distances[idx] if idx < len(distances) else None
        chunk = RetrievedChunk(
            chunk_id=str(metadata.get("chunk_id", "")),
            source_file=str(metadata.get("source_file", "")),
            text=str(document),
            char_start=int(metadata["char_start"]) if metadata.get("char_start") is not None else None,
            char_end=int(metadata["char_end"]) if metadata.get("char_end") is not None else None,
            distance=float(distance) if distance is not None else None,
        )
        chunks.append(chunk)

    elapsed_ms = (time.perf_counter() - start) * 1000
    _log(
        (
            f"collection={collection_name} requested_top_k={top_k} "
            f"returned_chunks={len(chunks)} retrieval_time_ms={elapsed_ms:.3f}"
        ),
        log_fn,
    )

    return RetrievalResult(
        question=question,
        requested_top_k=top_k,
        retrieval_time_ms=elapsed_ms,
        chunks=chunks,
    )
