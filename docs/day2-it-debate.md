# Day 2 IT Debate - Docker-first

Date: 2026-05-06  
Scope: Environment and dependency baseline for Day 2.

## Participants and ownership

- PM: Definition of Done and timeline alignment.
- Backend: app container contract and env naming.
- ML/RAG: model endpoint assumptions and retrieval defaults.
- DevOps: Docker runtime, ports, health checks, and troubleshooting flow.

## Final decisions

1. Runtime priority is Docker-first (`docker compose` as default entry point).
2. `app` service is mandatory in Day 2 baseline; ingestion/retrieval services are added incrementally in later days.
3. `.env.example` is the single config contract for local development.
4. Streamlit health endpoint (`/_stcore/health`) is the primary smoke check.
5. Local `venv` remains a diagnostic fallback, not the default workflow.

## Agreed technical contract

- App port is configurable through `APP_PORT` and defaults to `8501`.
- Model endpoint is provided through `OLLAMA_BASE_URL`.
- Default model identifiers are defined in env (`LLM_MODEL`, `EMBEDDING_MODEL`).
- Data and persistence paths are explicit (`DATA_DIR`, `CHROMA_PERSIST_DIR`).

## Risks and mitigations

- Risk: Docker port conflicts on `8501`.
  - Mitigation: override `APP_PORT` in `.env` per machine.
- Risk: File permission or volume mount issues on host.
  - Mitigation: keep bind mount minimal and use fallback venv for isolation debugging.
- Risk: Local model endpoint unavailable.
  - Mitigation: verify Ollama availability separately and keep app startup independent of generation calls on Day 2.
- Risk: Dependency drift across environments.
  - Mitigation: use image-based setup and a single `requirements.txt` source of truth.

## Day 2 acceptance checklist

- [x] `docker compose up --build -d` completes successfully.
- [x] `docker compose ps` shows app service up and healthy.
- [x] `curl http://localhost:8501/_stcore/health` returns `ok`.
- [x] `.env.example` exists and documents required variables.
- [x] README includes Docker quick start and fallback diagnostics.
