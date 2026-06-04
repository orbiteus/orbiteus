# ADR-0005: pgvector for embeddings

- **Status:** Accepted
- **Date:** 2026-05-03
- **Context tags:** backend, ai, data

## Context

Semantic search on records (people, leads, projects) needs vector similarity.
Adding a separate vector DB (Qdrant, Weaviate) increases operational footprint
significantly.

## Decision

Use `pgvector` extension on the existing PostgreSQL 16 instance. Image:
`pgvector/pgvector:pg16`. Table `base_embedding` stores `(tenant_id, model,
record_id, provider, model_name, dim, vector)` with an HNSW index.

## Consequences

- One database, one backup, one migration story.
- Vector queries co-located with metadata queries (no cross-store joins).
- HNSW recall and latency are competitive for typical CRM scales.
- Switching to a dedicated vector DB later is straightforward (data is in
  rows; rewrite the `embeddings.py` adapter).

## Alternatives considered

- Qdrant — excellent product; rejected to keep stack boring and stores few.
- Weaviate — same reasoning; also broader scope than we need.
- Lance / Milvus — niche; rejected.

## References

- `docs/15-ai-layer.md`
- `docs/04-data-model.md`
