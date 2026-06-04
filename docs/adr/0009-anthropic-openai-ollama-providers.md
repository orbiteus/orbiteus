# ADR-0009: AI providers — Anthropic + OpenAI + Ollama in MVP

- **Status:** Accepted
- **Date:** 2026-05-03
- **Context tags:** ai, vendors, scope

## Context

Engine ships with an AI layer ready for BYOK. We need a small, sensible set
of providers that covers most real adopters.

## Decision

MVP supports three providers via the `Provider` ABC:

- **Anthropic** (Claude) — default. Strong tool calling + writing quality.
- **OpenAI** — secondary. Universal compatibility, broad model selection.
- **Ollama** — optional local fallback for air-gapped or cost-sensitive
  deployments.

Azure OpenAI returns as an `OpenAI`-derived adapter in v0.2+. Other providers
require a new ADR.

## Consequences

- Adopters pick a provider per tenant via `base_ai_credential`.
- Engine never ships with a default provider key.
- Provider differences (function-calling shape, streaming events) are absorbed
  in `providers/` adapters.

## Alternatives considered

- Anthropic only — limits adopter freedom and creates lock-in.
- "Bring any provider" without curated list — increases bug surface and AI
  hallucination across SDK quirks.

## References

- `docs/15-ai-layer.md`
- `docs/16-ai-recipes.md`
