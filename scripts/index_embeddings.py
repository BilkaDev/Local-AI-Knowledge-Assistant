import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rag.indexing import index_chunks_to_chroma


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate embeddings from ingestion chunks and persist vectors to ChromaDB."
    )
    parser.add_argument(
        "--ingest-report",
        default=os.getenv("INGEST_REPORT_PATH", "artifacts/ingest/latest.json"),
        help="Path to ingestion report JSON containing chunk records.",
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
        "--batch-size",
        type=int,
        default=int(os.getenv("EMBEDDING_BATCH_SIZE", "32")),
        help="Number of chunks embedded per batch.",
    )
    parser.add_argument(
        "--report-path",
        default=os.getenv("INDEX_REPORT_PATH", "artifacts/index/latest.json"),
        help="Path where indexing report JSON will be written.",
    )
    return parser


def _read_chunks(ingest_report_path: Path) -> list[dict[str, Any]]:
    payload = json.loads(ingest_report_path.read_text(encoding="utf-8"))
    chunks = payload.get("chunks")
    if not isinstance(chunks, list):
        raise ValueError("Invalid ingestion report: `chunks` must be a list.")
    return chunks


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    ingest_report = Path(args.ingest_report)
    persist_dir = Path(args.persist_dir)
    report_path = Path(args.report_path)

    if not ingest_report.exists():
        print(f"[index] fatal_error: ingest report does not exist: {ingest_report}", file=sys.stderr)
        return 1

    try:
        chunks = _read_chunks(ingest_report)
        result = index_chunks_to_chroma(
            chunks=chunks,
            embedding_model=args.embedding_model,
            collection_name=args.collection_name,
            persist_dir=persist_dir,
            batch_size=args.batch_size,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[index] fatal_error: {exc}", file=sys.stderr)
        return 1

    payload = {
        "ingest_report": str(ingest_report),
        "embedding_model": args.embedding_model,
        "collection_name": args.collection_name,
        "persist_dir": str(persist_dir),
        **result.to_dict(),
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print("[index] completed")
    print(f"[index] ingest_report={ingest_report}")
    print(f"[index] embedding_model={args.embedding_model}")
    print(f"[index] collection_name={args.collection_name}")
    print(f"[index] chunks_processed={result.chunks_processed}")
    print(f"[index] vectors_saved={result.vectors_saved}")
    print(f"[index] collection_count={result.collection_count}")
    print(f"[index] failures={len(result.failures)}")
    print(f"[index] report_path={report_path}")

    if result.failures:
        print("[index] failure_details:")
        for failure in result.failures:
            print(f"  - chunk_ref={failure.chunk_ref} reason={failure.reason}")

    if result.collection_count == 0:
        print("[index] fatal_error: collection_count is 0 after indexing run", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
