# Day 3 IT Debate - Document ingestion (PDF/TXT)

Date: 2026-05-06  
Scope: Loader, chunking, and CLI ingestion baseline for Day 3.

## Participants and ownership

- PM: scope control and Definition of Done.
- Backend: ingestion module structure and CLI contract.
- ML/RAG: chunking strategy and retrieval impact.
- DevOps: Docker runtime compatibility and file paths.

## Two considered approaches

1. Minimal loader-first
   - Pros: fastest delivery, simple to debug.
   - Cons: weaker quality if chunking is too naive.
2. Quality-first chunking
   - Pros: better retrieval relevance from the start.
   - Cons: higher implementation and tuning effort on Day 3.

## Final decision

We choose a hybrid baseline:
1. Implement robust PDF/TXT loading first.
2. Add configurable chunking (`chunk_size`, `chunk_overlap`) on Day 3 itself.
3. Keep normalization minimal and deterministic (whitespace cleanup only).
4. Add CLI `ingest` command with clear report output.
5. Keep persistence path Docker-friendly (`/workspace/...`) and aligned with `.env`.

## Agreed technical contract (Day 3)

- Input directory: `data/`.
- Supported file types in scope: `.pdf`, `.txt`.
- Chunk metadata minimum: source filename, chunk id, character span or index.
- CLI output minimum: files scanned, files ingested, chunks produced, failures.
- Error policy: skip corrupted files, continue processing, report all failures.

## Risks and mitigations

- Risk: PDF parsing inconsistencies between files.
  - Mitigation: isolate loader logic per extension and log parser failures per file.
- Risk: Bad chunking parameters reduce retrieval quality.
  - Mitigation: expose `chunk_size` and `chunk_overlap` as env or CLI parameters.
- Risk: Ingestion time grows with file size.
  - Mitigation: add per-file timing in logs and optimize later if needed.
- Risk: Path mismatch in Docker vs host.
  - Mitigation: keep all runtime paths rooted in `/workspace` and configurable by env.

## Day 3 acceptance checklist (pre-implementation agreement)

- [ ] Loader reads `.pdf` and `.txt` from `data/`.
- [ ] Chunking is applied with configurable size and overlap.
- [ ] CLI `ingest` runs from container and prints ingestion summary.
- [ ] Failures are reported without crashing full ingestion run.
- [ ] Output is ready to hand over to Day 4 (embeddings + ChromaDB).
