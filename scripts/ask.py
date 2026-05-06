import argparse
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rag.generation import generate_answer


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run retrieval + generation and return grounded answer with sources."
    )
    parser.add_argument(
        "--question",
        required=True,
        help="User question answered against indexed local documents.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=int(os.getenv("RETRIEVAL_TOP_K", os.getenv("TOP_K", "4"))),
        help="Maximum number of chunks retrieved from ChromaDB.",
    )
    parser.add_argument(
        "--persist-dir",
        default=os.getenv("CHROMA_PERSIST_DIR", "artifacts/chroma"),
        help="Directory used by ChromaDB persistent storage.",
    )
    parser.add_argument(
        "--collection-name",
        default=os.getenv("CHROMA_COLLECTION_NAME", os.getenv("CHROMA_COLLECTION", "rag_chunks")),
        help="Target ChromaDB collection name.",
    )
    parser.add_argument(
        "--embedding-model",
        default=os.getenv("EMBEDDING_MODEL", "nomic-embed-text"),
        help="Ollama embedding model name.",
    )
    parser.add_argument(
        "--llm-model",
        default=os.getenv("LLM_MODEL", "llama3"),
        help="Ollama chat model used to generate the final answer.",
    )
    parser.add_argument(
        "--max-context-distance",
        type=float,
        default=None,
        help="Optional max distance threshold. Chunks above threshold are ignored.",
    )
    parser.add_argument(
        "--report-path",
        default="",
        help="Optional path where generation output JSON will be written.",
    )
    return parser


def _distance_threshold(args: argparse.Namespace) -> float | None:
    if args.max_context_distance is not None:
        return args.max_context_distance
    raw = os.getenv("RETRIEVAL_MAX_DISTANCE", "").strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError("RETRIEVAL_MAX_DISTANCE must be a float.") from exc


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    try:
        result = generate_answer(
            question=args.question,
            top_k=args.top_k,
            collection_name=args.collection_name,
            persist_dir=Path(args.persist_dir),
            embedding_model=args.embedding_model,
            llm_model=args.llm_model,
            max_context_distance=_distance_threshold(args),
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[ask] fatal_error: {exc}", file=sys.stderr)
        return 1

    payload = {
        "collection_name": args.collection_name,
        "persist_dir": args.persist_dir,
        "embedding_model": args.embedding_model,
        "llm_model": args.llm_model,
        **result.to_dict(),
    }
    if args.report_path:
        report_path = Path(args.report_path)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"[ask] report_path={report_path}")

    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
