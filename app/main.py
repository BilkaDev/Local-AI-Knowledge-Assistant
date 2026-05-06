import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rag.generation import GenerationResult, SourceCitation, generate_answer

FALLBACK_ERROR_MESSAGE = (
    "Wystapil blad podczas przetwarzania pytania. Sprawdz logi aplikacji i konfiguracje."
)
MODEL_PULL_ERROR_MESSAGE = "Nie udalo sie pobrac wybranego modelu z Ollama."
MODEL_MEMORY_ERROR_MESSAGE = (
    "Wybrany model wymaga wiecej RAM niz jest dostepne. "
    "Wybierz mniejszy model (np. `llama3.2:1b`, `phi3`, `qwen2.5:1.5b`) "
    "lub uruchom z wieksza pamiecia."
)
MODEL_TIMEOUT_ERROR_MESSAGE = (
    "Model nie odpowiedzial w limicie czasu. "
    "Wybierz mniejszy model albo zwieksz `OLLAMA_REQUEST_TIMEOUT_SECONDS`."
)


@dataclass
class AppConfig:
    top_k: int
    persist_dir: Path
    collection_name: str
    embedding_model: str
    llm_model: str
    max_context_distance: float | None


def _list_ollama_models(host: str) -> tuple[list[str], dict[str, int], str | None]:
    def _to_mapping(value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            return value
        if hasattr(value, "model_dump"):
            try:
                dumped = value.model_dump()
                if isinstance(dumped, dict):
                    return dumped
            except Exception:  # noqa: BLE001
                return {}
        if hasattr(value, "dict"):
            try:
                dumped = value.dict()
                if isinstance(dumped, dict):
                    return dumped
            except Exception:  # noqa: BLE001
                return {}
        if hasattr(value, "__dict__"):
            raw = getattr(value, "__dict__", {})
            if isinstance(raw, dict):
                return raw
        return {}

    try:
        import ollama

        client = ollama.Client(host=host)
        response = client.list()
    except Exception as exc:  # noqa: BLE001
        return [], {}, str(exc)

    response_map = _to_mapping(response)
    raw_models = response_map.get("models")
    if raw_models is None and hasattr(response, "models"):
        raw_models = getattr(response, "models")
    if raw_models is None:
        return [], {}, "Niepoprawny format odpowiedzi z Ollama list."
    if not isinstance(raw_models, list):
        try:
            raw_models = list(raw_models)
        except TypeError:
            return [], {}, "Niepoprawny format odpowiedzi z Ollama list."

    models: list[str] = []
    model_sizes: dict[str, int] = {}
    if not isinstance(raw_models, list):
        return [], {}, "Niepoprawny format odpowiedzi z Ollama list."

    for entry in raw_models:
        entry_map = _to_mapping(entry)
        if not entry_map:
            continue
        model_name = entry_map.get("model") or entry_map.get("name")
        if isinstance(model_name, str) and model_name and model_name not in models:
            models.append(model_name)
        model_size = entry_map.get("size")
        if isinstance(model_name, str) and isinstance(model_size, int) and model_size > 0:
            model_sizes[model_name] = model_size
    return models, model_sizes, None


def _is_model_available(model_name: str, available_models: list[str]) -> bool:
    target = model_name.strip()
    if not target:
        return False
    target_base = target.split(":", maxsplit=1)[0]
    for available in available_models:
        candidate = available.strip()
        if candidate == target:
            return True
        if candidate.split(":", maxsplit=1)[0] == target_base:
            return True
    return False


def _pull_ollama_model(host: str, model_name: str) -> str | None:
    try:
        import ollama

        client = ollama.Client(host=host)
        client.pull(model=model_name)
        return None
    except Exception as exc:  # noqa: BLE001
        return str(exc)


def _resolve_available_model_name(requested_model: str, available_models: list[str]) -> str:
    requested = requested_model.strip()
    if not requested:
        return requested_model
    if requested in available_models:
        return requested
    requested_base = requested.split(":", maxsplit=1)[0]
    for model in available_models:
        if model.split(":", maxsplit=1)[0] == requested_base:
            return model
    return requested_model


def _is_memory_error(error_message: str) -> bool:
    lowered = error_message.lower()
    return "requires more system memory" in lowered and "than is available" in lowered


def _is_model_capacity_error(error_message: str) -> bool:
    lowered = error_message.lower()
    return _is_memory_error(lowered) or (
        "runner process has terminated" in lowered and "status code: 500" in lowered
    )


def _is_timeout_error(error_message: str) -> bool:
    lowered = error_message.lower()
    return "timed out" in lowered or "timeout" in lowered


def _parse_model_size_billions(model_name: str) -> float | None:
    lowered = model_name.lower()
    match = re.search(r"(\d+(?:\.\d+)?)b", lowered)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def _fallback_models(
    current_model: str,
    available_models: list[str],
    model_sizes: dict[str, int],
) -> list[str]:
    candidates = [
        model
        for model in available_models
        if model != current_model
    ]
    if not candidates:
        return []

    def _sort_key(model_name: str) -> tuple[int, float, str]:
        if model_name in model_sizes:
            return (0, float(model_sizes[model_name]), model_name)
        parsed_size = _parse_model_size_billions(model_name)
        if parsed_size is not None:
            return (1, parsed_size, model_name)
        return (2, float("inf"), model_name)

    return sorted(candidates, key=_sort_key)


def _run_generation(
    prompt: str,
    config: AppConfig,
    llm_model: str,
) -> GenerationResult:
    return generate_answer(
        question=prompt,
        top_k=config.top_k,
        collection_name=config.collection_name,
        persist_dir=config.persist_dir,
        embedding_model=config.embedding_model,
        llm_model=llm_model,
        max_context_distance=config.max_context_distance,
        log_fn=None,
    )


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _float_env(name: str) -> float | None:
    raw = os.getenv(name, "").strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _load_config() -> AppConfig:
    top_k = _int_env("RETRIEVAL_TOP_K", default=_int_env("TOP_K", 4))
    return AppConfig(
        top_k=top_k,
        persist_dir=Path(os.getenv("CHROMA_PERSIST_DIR", "artifacts/chroma")),
        collection_name=os.getenv("CHROMA_COLLECTION_NAME", os.getenv("CHROMA_COLLECTION", "rag_chunks")),
        embedding_model=os.getenv("EMBEDDING_MODEL", "nomic-embed-text"),
        llm_model=os.getenv("LLM_MODEL", "llama3"),
        max_context_distance=_float_env("RETRIEVAL_MAX_DISTANCE"),
    )


def _render_source(source: SourceCitation) -> None:
    chunk_label = source.chunk_id or "unknown_chunk"
    source_label = source.source_file or "unknown_source"
    st.markdown(f"- `{source_label}` / `{chunk_label}`")
    details = []
    if source.distance is not None:
        details.append(f"distance={source.distance:.4f}")
    if source.char_start is not None and source.char_end is not None:
        details.append(f"chars={source.char_start}-{source.char_end}")
    if details:
        st.caption(", ".join(details))
    if source.snippet:
        st.caption(f"Snippet: {source.snippet}")


def _render_assistant_message(message: dict[str, Any]) -> None:
    st.markdown(message["content"])
    sources = message.get("sources", [])
    if sources:
        with st.expander("Zrodla", expanded=False):
            for source in sources:
                _render_source(source)
    fallback_reason = message.get("fallback_reason")
    if fallback_reason:
        st.caption(f"Fallback reason: `{fallback_reason}`")


def _append_assistant_result(result: GenerationResult) -> None:
    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": result.answer_text,
            "sources": result.sources,
            "fallback_reason": result.fallback_reason,
        }
    )


def _append_assistant_error(error_message: str) -> None:
    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": error_message,
            "sources": [],
            "fallback_reason": "runtime_error",
        }
    )


def _init_session_state() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "selected_model" not in st.session_state:
        st.session_state.selected_model = None


def _render_model_selector(
    default_model: str,
    ollama_base_url: str,
) -> tuple[str, list[str], dict[str, int]]:
    st.sidebar.subheader("Ustawienia modelu")
    st.sidebar.markdown("Lista modeli: [ollama.com/library](https://ollama.com/library)")
    models, model_sizes, list_error = _list_ollama_models(host=ollama_base_url)

    options = list(models)
    preferred_model = st.session_state.selected_model or default_model
    if preferred_model and preferred_model not in options:
        options.insert(0, preferred_model)

    if options:
        default_index = options.index(preferred_model) if preferred_model in options else 0
        selected_from_list = st.sidebar.selectbox(
            "Model odpowiedzi (LLM)",
            options=options,
            index=default_index,
            key="selected_model_from_list",
            help="Modele sa pobierane dynamicznie z lokalnego Ollama.",
        )
    else:
        selected_from_list = preferred_model

    manual_model = st.sidebar.text_input(
        "Lub wpisz model recznie",
        value="",
        key="manual_model_input",
        placeholder="np. llama3.1",
        help="Jesli pole nie jest puste, nadpisze wybor z listy.",
    ).strip()

    if list_error:
        st.sidebar.warning(
            "Nie udalo sie pobrac listy modeli z Ollama. "
            "Mozesz wpisac nazwe modelu recznie."
        )
        st.sidebar.caption(f"Szczegoly: `{list_error}`")

    active_model = manual_model or selected_from_list
    st.session_state.selected_model = active_model
    if active_model and not _is_model_available(active_model, models):
        st.sidebar.caption("Model nie jest lokalnie dostepny - zostanie pobrany przy pierwszym pytaniu.")
    st.sidebar.caption(f"Aktywny model: `{active_model}`")
    return active_model, models, model_sizes


def main() -> None:
    st.set_page_config(page_title="Local AI Knowledge Assistant", page_icon=":robot_face:")
    st.title("Local AI Knowledge Assistant")
    st.caption("Day 7 MVP chat: retrieval-grounded answers with source snippets.")

    _init_session_state()
    config = _load_config()
    ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    llm_model, available_models, model_sizes = _render_model_selector(
        default_model=config.llm_model,
        ollama_base_url=ollama_base_url,
    )

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if message["role"] == "assistant":
                _render_assistant_message(message)
            else:
                st.markdown(message["content"])

    prompt = st.chat_input("Zadaj pytanie do lokalnej bazy wiedzy")
    if not prompt:
        return

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            if not _is_model_available(llm_model, available_models):
                with st.spinner(f"Pobieram model `{llm_model}` z Ollama..."):
                    pull_error = _pull_ollama_model(
                        host=ollama_base_url,
                        model_name=llm_model,
                    )
                if pull_error:
                    st.error(MODEL_PULL_ERROR_MESSAGE)
                    st.caption(f"Szczegoly: `{pull_error}`")
                    _append_assistant_error(MODEL_PULL_ERROR_MESSAGE)
                    return
                available_models, model_sizes, _ = _list_ollama_models(host=ollama_base_url)
                llm_model = _resolve_available_model_name(llm_model, available_models)
                st.session_state.selected_model = llm_model
                st.caption(f"Model `{llm_model}` zostal pobrany.")

            with st.spinner("Wyszukuje kontekst i generuje odpowiedz..."):
                result = _run_generation(
                    prompt=prompt,
                    config=config,
                    llm_model=llm_model,
                )
            if result.fallback_reason == "empty_generation":
                retry_models = _fallback_models(
                    current_model=llm_model,
                    available_models=available_models,
                    model_sizes=model_sizes,
                )
                for retry_model in retry_models:
                    st.warning(
                        f"Model `{llm_model}` nie zwrocil tresci odpowiedzi. "
                        f"Probuję fallback: `{retry_model}`."
                    )
                    with st.spinner(f"Generuje odpowiedz modelem `{retry_model}`..."):
                        retry_result = _run_generation(
                            prompt=prompt,
                            config=config,
                            llm_model=retry_model,
                        )
                    if retry_result.fallback_reason != "empty_generation":
                        result = retry_result
                        st.caption(
                            f"Uzyto fallback modelu `{retry_model}` z powodu pustej odpowiedzi."
                        )
                        break
            _append_assistant_result(result)
            _render_assistant_message(st.session_state.messages[-1])
        except Exception as exc:  # noqa: BLE001
            error_message = str(exc)
            if _is_model_capacity_error(error_message):
                retry_models = _fallback_models(
                    current_model=llm_model,
                    available_models=available_models,
                    model_sizes=model_sizes,
                )
                if retry_models:
                    for retry_model in retry_models:
                        st.warning(
                            f"Model `{llm_model}` nie moze stabilnie wystartowac. "
                            f"Probuję fallback: `{retry_model}`."
                        )
                        try:
                            with st.spinner(f"Generuje odpowiedz modelem `{retry_model}`..."):
                                fallback_result = _run_generation(
                                    prompt=prompt,
                                    config=config,
                                    llm_model=retry_model,
                                )
                            _append_assistant_result(fallback_result)
                            _render_assistant_message(st.session_state.messages[-1])
                            st.caption(
                                f"Uzyto fallback modelu `{retry_model}` z powodu limitu zasobow."
                            )
                            return
                        except Exception as retry_exc:  # noqa: BLE001
                            if not _is_model_capacity_error(str(retry_exc)):
                                st.error(FALLBACK_ERROR_MESSAGE)
                                st.caption(f"Szczegoly: `{retry_exc}`")
                                _append_assistant_error(FALLBACK_ERROR_MESSAGE)
                                return

                st.error(MODEL_MEMORY_ERROR_MESSAGE)
                st.caption(f"Szczegoly: `{error_message}`")
                _append_assistant_error(MODEL_MEMORY_ERROR_MESSAGE)
                return

            if _is_timeout_error(error_message):
                st.error(MODEL_TIMEOUT_ERROR_MESSAGE)
                st.caption(f"Szczegoly: `{error_message}`")
                _append_assistant_error(MODEL_TIMEOUT_ERROR_MESSAGE)
                return

            st.error(FALLBACK_ERROR_MESSAGE)
            st.caption(f"Szczegoly: `{error_message}`")
            _append_assistant_error(FALLBACK_ERROR_MESSAGE)


if __name__ == "__main__":
    main()
