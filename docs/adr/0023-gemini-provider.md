# ADR-0023: Gemini as fourth BYOK chat provider

- **Status:** Accepted
- **Date:** 2026-05-29
- **Context tags:** ai, vendors, gemini
- **Supersedes (partially):** ADR-0009 scope list

## Context

Adopters increasingly standardise on Google Gemini (Gemini API / AI Studio keys).
ADR-0009 limited MVP to Anthropic, OpenAI, and Ollama. The `Provider` ABC already
isolates SDK differences; adding Gemini is a bounded adapter change.

Embeddings remain on OpenAI (or Ollama locally) — pgvector dimensions and the
existing refresh pipeline are unchanged.

## Decision

Add **Gemini** (`provider=gemini`) as a fourth curated BYOK provider:

- SDK: `google-genai` (Apache-2.0)
- Default chat model: `gemini-2.0-flash`
- Chat + tool calling via `client.aio.models.generate_content`
- Embeddings: **not supported** on this provider (same policy as Anthropic)

## Consequences

- Admin UI provider dropdown includes Google Gemini.
- `POST /api/ai/credentials` accepts `gemini` and pings before persist.
- System status “Provider adapters” probe includes `gemini`.

## Alternatives considered

- Vertex AI only — heavier setup; AI Studio keys cover most adopters first.
- Re-use OpenAI-compatible Gemini endpoint — non-standard, harder to maintain.

## References

- ADR-0009, ADR-0004
- `docs/15-ai-layer.md`
