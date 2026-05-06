import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from rag.retrieval import RetrievedChunk, retrieve_similar_chunks

SOURCE_SNIPPET_MAX_CHARS = 240
DEFAULT_OLLAMA_TIMEOUT_SECONDS = 120.0
DEFAULT_LLM_MAX_TOKENS = 256


@dataclass
class SourceCitation:
    chunk_id: str
    source_file: str
    char_start: int | None
    char_end: int | None
    distance: float | None
    snippet: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "source_file": self.source_file,
            "char_start": self.char_start,
            "char_end": self.char_end,
            "distance": self.distance,
            "snippet": self.snippet,
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


def _create_ollama_client(host: str, timeout_seconds: float | None = None) -> Any:
    import ollama

    if timeout_seconds is None:
        return ollama.Client(host=host)
    try:
        return ollama.Client(host=host, timeout=timeout_seconds)
    except TypeError:
        return ollama.Client(host=host)


def _float_env(name: str, default: float) -> float:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError:
        return default
    if value <= 0:
        return default
    return value


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    if value <= 0:
        return default
    return value


def _ollama_generate_options() -> dict[str, int]:
    return {"num_predict": _int_env("LLM_MAX_TOKENS", DEFAULT_LLM_MAX_TOKENS)}


def _build_snippet(text: str, max_chars: int = SOURCE_SNIPPET_MAX_CHARS) -> str:
    normalized = " ".join(text.strip().split())
    if len(normalized) <= max_chars:
        return normalized
    return f"{normalized[: max_chars - 1].rstrip()}..."


def _to_source(chunk: RetrievedChunk) -> SourceCitation:
    return SourceCitation(
        chunk_id=chunk.chunk_id,
        source_file=chunk.source_file,
        char_start=chunk.char_start,
        char_end=chunk.char_end,
        distance=chunk.distance,
        snippet=_build_snippet(chunk.text),
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


def _build_generate_prompt(question: str, chunks: list[RetrievedChunk]) -> str:
    context_block = _build_context(chunks)
    return (
        "Jestes asystentem opartym o retrieval. Uzywaj tylko podanego kontekstu.\n\n"
        f"Kontekst:\n{context_block}\n\n"
        f"Pytanie: {question}\n\n"
        "Zasady:\n"
        "1) Odpowiadaj tylko na podstawie kontekstu.\n"
        "2) Jesli kontekst nie wystarcza, napisz to wprost.\n"
        "3) Odpowiedz ma byc zwiezla i konkretna.\n"
    )


def _extract_chat_content(response: dict[str, Any]) -> str:
    def _string_from_value(value: Any) -> str:
        if isinstance(value, str):
            return value.strip()
        if isinstance(value, list):
            parts: list[str] = []
            for item in value:
                if isinstance(item, str) and item.strip():
                    parts.append(item.strip())
                elif isinstance(item, dict):
                    text = item.get("text") or item.get("content")
                    if isinstance(text, str) and text.strip():
                        parts.append(text.strip())
            return "\n".join(parts).strip()
        if isinstance(value, dict):
            text = value.get("text") or value.get("content") or value.get("response")
            if isinstance(text, str):
                return text.strip()
        return ""

    message = response.get("message")
    if isinstance(message, dict):
        content = _string_from_value(message.get("content"))
        if content:
            return content

    for key in ("response", "output_text", "content"):
        candidate = _string_from_value(response.get(key))
        if candidate:
            return candidate

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
    timeout_seconds = _float_env("OLLAMA_REQUEST_TIMEOUT_SECONDS", DEFAULT_OLLAMA_TIMEOUT_SECONDS)
    client = _create_ollama_client(host=host, timeout_seconds=timeout_seconds)
    messages = _build_messages(question=question, chunks=selected_chunks)
    generate_options = _ollama_generate_options()
    generation_start = time.perf_counter()
    response = client.chat(model=llm_model, messages=messages, options=generate_options)
    generation_time_ms = (time.perf_counter() - generation_start) * 1000
    try:
        answer_text = _extract_chat_content(response)
    except ValueError:
        generate_prompt = _build_generate_prompt(question=question, chunks=selected_chunks)
        generate_start = time.perf_counter()
        generate_response = client.generate(
            model=llm_model,
            prompt=generate_prompt,
            options=generate_options,
        )
        generation_time_ms += (time.perf_counter() - generate_start) * 1000
        try:
            answer_text = _extract_chat_content(generate_response)
        except ValueError:
            _log(
                (
                    f"model={llm_model} used_chunks={len(selected_chunks)} "
                    "fallback_reason=empty_generation generation_time_ms="
                    f"{generation_time_ms:.3f}"
                ),
                log_fn,
            )
            return GenerationResult(
                question=question,
                answer_text=(
                    "Model nie zwrocil tresci odpowiedzi. "
                    "Sprobuj ponownie lub wybierz inny model."
                ),
                model=llm_model,
                used_chunks=len(selected_chunks),
                sources=sources,
                retrieval_time_ms=retrieval_result.retrieval_time_ms,
                generation_time_ms=generation_time_ms,
                fallback_reason="empty_generation",
            )

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
