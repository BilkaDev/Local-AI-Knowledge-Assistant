import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from rag.retrieval import RetrievedChunk, retrieve_similar_chunks


@dataclass
class SourceCitation:
    chunk_id: str
    source_file: str
    char_start: int | None
    char_end: int | None
    distance: float | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "source_file": self.source_file,
            "char_start": self.char_start,
            "char_end": self.char_end,
            "distance": self.distance,
        }


@dataclass
class GenerationResult:
    question: str
    answer_text: str
    model: str
    used_chunks: int
    sources: list[SourceCitation]
    retrieval_time_ms: float
    generation_time_ms: float
    fallback_reason: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "answer_text": self.answer_text,
            "model": self.model,
            "used_chunks": self.used_chunks,
            "sources": [source.to_dict() for source in self.sources],
            "retrieval_time_ms": round(self.retrieval_time_ms, 3),
            "generation_time_ms": round(self.generation_time_ms, 3),
            "fallback_reason": self.fallback_reason,
        }


def _log(message: str, log_fn: Callable[[str], None] | None) -> None:
    if log_fn is None:
        return
    log_fn(f"[generation] {message}")


def _create_ollama_client(host: str) -> Any:
    import ollama

    return ollama.Client(host=host)


def _to_source(chunk: RetrievedChunk) -> SourceCitation:
    return SourceCitation(
        chunk_id=chunk.chunk_id,
        source_file=chunk.source_file,
        char_start=chunk.char_start,
        char_end=chunk.char_end,
        distance=chunk.distance,
    )


def _build_context(chunks: list[RetrievedChunk]) -> str:
    context_parts: list[str] = []
    for idx, chunk in enumerate(chunks, start=1):
        location = f"{chunk.char_start}-{chunk.char_end}" if chunk.char_start is not None else "unknown"
        context_parts.append(
            "\n".join(
                [
                    f"[{idx}] source_file={chunk.source_file}",
                    f"chunk_id={chunk.chunk_id}",
                    f"char_range={location}",
                    f"content={chunk.text}",
                ]
            )
        )
    return "\n\n".join(context_parts)


def _build_messages(question: str, chunks: list[RetrievedChunk]) -> list[dict[str, str]]:
    context_block = _build_context(chunks)
    system_prompt = (
        "You are a retrieval-grounded assistant. "
        "Use only provided context. If context is insufficient, say it explicitly. "
        "Do not invent facts."
    )
    user_prompt = (
        "Kontekst:\n"
        f"{context_block}\n\n"
        "Pytanie użytkownika:\n"
        f"{question}\n\n"
        "Zasady odpowiedzi:\n"
        "1) Odpowiadaj wyłącznie na podstawie kontekstu.\n"
        "2) Gdy brak danych, napisz wyraźnie że nie masz wystarczającego kontekstu.\n"
        "3) Nie cytuj źródeł w treści odpowiedzi listą numerowaną ani markdown links.\n"
        "4) Odpowiedź ma być zwięzła i konkretna."
    )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def _extract_chat_content(response: dict[str, Any]) -> str:
    message = response.get("message")
    if isinstance(message, dict):
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            return content.strip()

    fallback = response.get("response")
    if isinstance(fallback, str) and fallback.strip():
        return fallback.strip()

    raise ValueError("Ollama chat response missing generated text.")


def _filter_relevant_chunks(
    chunks: list[RetrievedChunk], max_context_distance: float | None
) -> tuple[list[RetrievedChunk], str | None]:
    if not chunks:
        return [], "no_context"
    if max_context_distance is None:
        return chunks, None

    filtered = [
        chunk
        for chunk in chunks
        if chunk.distance is None or chunk.distance <= max_context_distance
    ]
    if filtered:
        return filtered, None
    return [], "low_relevance"


def generate_answer(
    question: str,
    top_k: int,
    collection_name: str,
    persist_dir: Path,
    embedding_model: str,
    llm_model: str,
    max_context_distance: float | None = None,
    log_fn: Callable[[str], None] | None = print,
) -> GenerationResult:
    retrieval_result = retrieve_similar_chunks(
        question=question,
        top_k=top_k,
        collection_name=collection_name,
        persist_dir=persist_dir,
        embedding_model=embedding_model,
        log_fn=log_fn,
    )
    selected_chunks, fallback_reason = _filter_relevant_chunks(
        chunks=retrieval_result.chunks,
        max_context_distance=max_context_distance,
    )

    sources = [_to_source(chunk) for chunk in selected_chunks]
    if fallback_reason is not None:
        answer_text = (
            "Nie mam wystarczającego kontekstu w bazie wiedzy, aby udzielić wiarygodnej odpowiedzi."
        )
        _log(
            (
                f"model={llm_model} used_chunks=0 fallback_reason={fallback_reason} "
                "generation_time_ms=0.000"
            ),
            log_fn,
        )
        return GenerationResult(
            question=question,
            answer_text=answer_text,
            model=llm_model,
            used_chunks=0,
            sources=[],
            retrieval_time_ms=retrieval_result.retrieval_time_ms,
            generation_time_ms=0.0,
            fallback_reason=fallback_reason,
        )

    host = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    client = _create_ollama_client(host=host)
    messages = _build_messages(question=question, chunks=selected_chunks)
    generation_start = time.perf_counter()
    response = client.chat(model=llm_model, messages=messages)
    generation_time_ms = (time.perf_counter() - generation_start) * 1000
    answer_text = _extract_chat_content(response)

    _log(
        (
            f"model={llm_model} used_chunks={len(selected_chunks)} fallback_reason=none "
            f"generation_time_ms={generation_time_ms:.3f}"
        ),
        log_fn,
    )
    return GenerationResult(
        question=question,
        answer_text=answer_text,
        model=llm_model,
        used_chunks=len(selected_chunks),
        sources=sources,
        retrieval_time_ms=retrieval_result.retrieval_time_ms,
        generation_time_ms=generation_time_ms,
        fallback_reason=None,
    )
