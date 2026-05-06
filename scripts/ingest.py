import argparse
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rag.ingestion import ingest_documents


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ingest PDF/TXT documents and create chunks.")
    parser.add_argument(
        "--data-dir",
        default=os.getenv("DATA_DIR", "data"),
        help="Directory containing source documents (default: DATA_DIR env or data).",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=int(os.getenv("CHUNK_SIZE", "900")),
        help="Character length of each chunk.",
    )
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=int(os.getenv("CHUNK_OVERLAP", "150")),
        help="Character overlap between consecutive chunks.",
    )
    parser.add_argument(
        "--report-path",
        default=os.getenv("INGEST_REPORT_PATH", "artifacts/ingest/latest.json"),
        help="Path where ingestion report JSON will be written.",
    )
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    report_path = Path(args.report_path)

    try:
        result = ingest_documents(
            data_dir=data_dir,
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[ingest] fatal_error: {exc}", file=sys.stderr)
        return 1

    report = result.to_dict()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("[ingest] completed")
    print(f"[ingest] data_dir={result.data_dir}")
    print(f"[ingest] files_scanned={result.files_scanned}")
    print(f"[ingest] files_ingested={result.files_ingested}")
    print(f"[ingest] chunks_created={result.chunks_created}")
    print(f"[ingest] failures={len(result.failures)}")
    print(f"[ingest] report_path={report_path}")

    if result.failures:
        print("[ingest] failure_details:")
        for failure in result.failures:
            print(f"  - file={failure.file} reason={failure.reason}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
