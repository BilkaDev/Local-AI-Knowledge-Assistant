# Day 4 IT Debate - Embeddings and ChromaDB

Date: 2026-05-06  
Scope: Embedding generation and vector persistence baseline for Day 4.

## Participants and ownership

- PM: delivery scope and Definition of Done.
- Backend: indexing flow and metadata contract continuity.
- ML/RAG: embedding model choice and retrieval-readiness quality bar.
- DevOps: persistence paths, runtime reproducibility, and Docker alignment.

## Two considered approaches

1. Fast path indexing
   - Description: generate embeddings and write directly to ChromaDB with minimal checks.
   - Pros: fastest implementation and shortest path to visible output.
   - Cons: higher risk of silent data inconsistencies and harder Day 5 debugging.
2. Stable contract-first indexing
   - Description: validate ingestion payload, enforce required metadata, then write to ChromaDB with summary reporting.
   - Pros: better reliability, clearer failure diagnosis, safer handoff to retrieval.
   - Cons: slightly more implementation effort on Day 4.

## Final decision

We choose the stable contract-first approach:
1. Reuse chunk schema from ingestion (`chunk_id`, `source_file`, `text`, `char_start`, `char_end`).
2. Generate embeddings with explicit model configuration (`EMBEDDING_MODEL`).
3. Persist vectors and metadata in a named ChromaDB collection.
4. Emit clear indexing summary (processed chunks, saved vectors, failures).
5. Keep runtime Docker-first and path config rooted in env variables.

## Agreed technical contract (Day 4)

- Input source: ingestion output chunks produced from `data/`.
- Required metadata per vector: `chunk_id`, `source_file`, `char_start`, `char_end`.
- Vector DB backend: ChromaDB persisted under configurable directory.
- Collection naming: explicit and stable via environment variable.
- Error policy: skip invalid chunk records, continue processing, report failures.

## Risks and mitigations

- Risk: embedding model mismatch between environments.
  - Mitigation: pin model name in `.env` and document defaults in README.
- Risk: inconsistent metadata breaks source attribution in Day 5.
  - Mitigation: validate required metadata keys before writing to ChromaDB.
- Risk: duplicate inserts after repeated indexing runs.
  - Mitigation: use deterministic ids based on `chunk_id` and source file.
- Risk: persistence path mismatch in Docker vs host.
  - Mitigation: keep path configurable through `CHROMA_PERSIST_DIR` and run through `docker compose`.

## Day 4 acceptance checklist (pre-implementation agreement)

- [ ] Embedding model is selected and configurable via env.
- [ ] Chunks are stored in ChromaDB with required metadata.
- [ ] Collection can be inspected and confirms non-zero vector count.
- [ ] Indexing run prints operational summary and failure details.
- [ ] Output is retrieval-ready for Day 5 without metadata contract changes.
