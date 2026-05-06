import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from pypdf import PdfReader


SUPPORTED_EXTENSIONS = {".pdf", ".txt"}


@dataclass
class IngestionFailure:
    file: str
    reason: str


@dataclass
class ChunkRecord:
    source_file: str
    chunk_id: str
    text: str
    char_start: int
    char_end: int


@dataclass
class IngestionResult:
    data_dir: str
    files_scanned: int
    files_ingested: int
    chunks_created: int
    chunk_size: int
    chunk_overlap: int
    chunks: list[ChunkRecord]
    failures: list[IngestionFailure]

    def to_dict(self) -> dict[str, Any]:
        return {
            "data_dir": self.data_dir,
            "files_scanned": self.files_scanned,
            "files_ingested": self.files_ingested,
            "chunks_created": self.chunks_created,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "chunks": [asdict(chunk) for chunk in self.chunks],
            "failures": [asdict(failure) for failure in self.failures],
        }


def _normalize_text(text: str) -> str:
    # Keep normalization deterministic and minimal for easier debugging.
    return re.sub(r"\s+", " ", text).strip()


def _chunk_text(text: str, chunk_size: int, chunk_overlap: int) -> list[tuple[int, int, str]]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0")
    if chunk_overlap < 0:
        raise ValueError("chunk_overlap cannot be negative")
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")

    chunks: list[tuple[int, int, str]] = []
    step = chunk_size - chunk_overlap
    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk_text = text[start:end].strip()
        if chunk_text:
            chunks.append((start, end, chunk_text))
        if end >= len(text):
            break
        start += step

    return chunks


def _load_txt(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _load_pdf(path: Path) -> str:
    reader = PdfReader(str(path))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages)


def _load_document(path: Path) -> str:
    extension = path.suffix.lower()
    if extension == ".txt":
        return _load_txt(path)
    if extension == ".pdf":
        return _load_pdf(path)
    raise ValueError(f"Unsupported extension: {extension}")


def ingest_documents(data_dir: Path, chunk_size: int, chunk_overlap: int) -> IngestionResult:
    if not data_dir.exists():
        raise FileNotFoundError(f"Data directory does not exist: {data_dir}")

    file_paths = sorted(
        p for p in data_dir.rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
    )

    chunk_records: list[ChunkRecord] = []
    failures: list[IngestionFailure] = []
    files_ingested = 0

    for file_path in file_paths:
        try:
            raw_text = _load_document(file_path)
            normalized = _normalize_text(raw_text)
            if not normalized:
                failures.append(IngestionFailure(file=str(file_path), reason="empty_content_after_normalization"))
                continue

            chunks = _chunk_text(normalized, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
            if not chunks:
                failures.append(IngestionFailure(file=str(file_path), reason="no_chunks_created"))
                continue

            for index, (start, end, text) in enumerate(chunks):
                chunk_records.append(
                    ChunkRecord(
                        source_file=str(file_path),
                        chunk_id=f"{file_path.stem}-{index:04d}",
                        text=text,
                        char_start=start,
                        char_end=end,
                    )
                )
            files_ingested += 1
        except Exception as exc:  # noqa: BLE001
            failures.append(IngestionFailure(file=str(file_path), reason=str(exc)))

    return IngestionResult(
        data_dir=str(data_dir),
        files_scanned=len(file_paths),
        files_ingested=files_ingested,
        chunks_created=len(chunk_records),
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        chunks=chunk_records,
        failures=failures,
    )
