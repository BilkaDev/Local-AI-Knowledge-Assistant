import argparse
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rag.retrieval import retrieve_similar_chunks


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Query ChromaDB and return top-k relevant chunks with source metadata."
    )
    parser.add_argument(
        "--question",
        required=True,
        help="User question used to search similar chunks.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=int(os.getenv("RETRIEVAL_TOP_K", "4")),
        help="Maximum number of chunks to retrieve.",
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
        "--report-path",
        default="",
        help="Optional path where retrieval output JSON will be written.",
    )
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    try:
        result = retrieve_similar_chunks(
            question=args.question,
            top_k=args.top_k,
            collection_name=args.collection_name,
            persist_dir=Path(args.persist_dir),
            embedding_model=args.embedding_model,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[retrieve] fatal_error: {exc}", file=sys.stderr)
        return 1

    payload = {
        "collection_name": args.collection_name,
        "persist_dir": args.persist_dir,
        "embedding_model": args.embedding_model,
        **result.to_dict(),
    }

    if args.report_path:
        report_path = Path(args.report_path)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"[retrieve] report_path={report_path}")

    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
