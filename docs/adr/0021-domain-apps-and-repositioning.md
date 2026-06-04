# ADR-0021: Domain-first positioning and hybrid UI

- **Status:** Accepted
- **Date:** 2026-05-29
- **Supersedes:** (addendum to) ADR-0001
- **Context tags:** strategy, frontend, ai-agents

## Context

After four months, Orbiteus positioning shifted:

- Primary goal is **not** to ship a generic ERP competing with modular
  ERP demos.
- Primary goal **is** an **AI agent engine** for **domain business apps**
  that fill operational gaps (CRM, HR, club ops, BI, integrations).
- A full Odoo-like surface (minus accounting localization hell) remains
  **architecturally possible** for ambitious adopters — the engine must
  not block that — but it is no longer the public mission.
- **CalTraining** (LadiesGym) is an **external reference product**: fitness-specific
  CRM replacing Pipedrive, connecting call center and trainers. It is **not**
  shipped in this repository.
- **`modules/crm`** is the **sole in-repo showcase domain module** — the
  reference implementation agents copy when building new modules.

## Decision

1. **Domain-first, engine-always:** Documentation and agent guardrails
   describe Orbiteus as an engine for AI-built domain apps. A **module
   is a domain app** (`modules/<name>/` with models, views, access, docs).

2. **CRM is the showcase:** `modules/crm` demonstrates the full stack —
   models, kanban/calendar/graph views, RBAC, audit, webhooks, AI hooks.
   New domain work follows the same module layout; CRM is the canonical
   example, not a throwaway demo.

3. **Hybrid UI model:**
   - **Tier A — Generic shell:** `admin-ui` dynamic routes +
     `GET /api/base/ui-config` → auto list/form/kanban/calendar/graph
     (80% of models).
   - **Tier B — Module feature routes:** optional dedicated React pages
     under `admin-ui/src/app/` (e.g. CRM pipeline dashboard) when XML-driven
     views are not enough. Same backend contracts (Auto-CRUD, RBAC, audit).
     Adopters may also ship a separate SPA in their own repo; the engine does
     not maintain a `templates/domain-app/` scaffold.

4. **Spec-driven agent workflow** is mandatory for non-trivial work
   (see `docs/39-spec-driven-agent-workflow.md`).

5. **Reference product doc:** `docs/40-reference-product-caltrain.md`
   describes the external exemplar without importing competitor ERP trademarks.

## Consequences

- README positioning paragraphs may emphasize domain apps; locked hero
  tagline unchanged per `AGENTS.md`.
- New modules start with `modules/<name>/docs/spec.md` before code.
- Performance patterns from reference products (Query, prefetch, expand)
  land in Tier A; bespoke CRM (or other module) screens stay in Tier B.
- Accounting / statutory ERP modules are **out of scope** for the
  engine maintainers; adopters may add them as modules.

## Alternatives considered

- **Merge CalTraining into monorepo** — rejected; external reference doc only.
- **Separate `templates/domain-app/` scaffold** — rejected; module = domain app,
  CRM is the living template.
- **Abandon generic admin-ui** — rejected: agents need zero-TSX CRUD for
  speed on simple models.

## References

- `docs/01-engine-positioning.md`
- `docs/26-canonical-crm.md`
- `docs/39-spec-driven-agent-workflow.md`
- `docs/40-reference-product-caltrain.md`
- ADR-0001
