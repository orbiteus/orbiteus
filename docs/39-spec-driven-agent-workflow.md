# 39 — Spec-driven agent workflow

> How humans and AI agents should build on Orbiteus: **Ask → Spec →
> Implement → Verify**. Minimizes prompt tokens and failed one-shots.

## Why

Orbiteus is built **for AI agents**, not for hand-coding every screen.
Agents that jump straight to code without updating specs drift from
guardrails (`pre-prompt.md`, RBAC, module boundaries) and burn tokens
re-discovering conventions.

## Phases

### 1. Ask (clarify)

Before any multi-file change, the agent (or human) must answer:

- **Domain:** Who uses this? What process does it replace?
- **Models:** New aggregate roots? FK targets in other modules?
- **Permissions:** Which roles read/write which models?
- **UI tier:** Generic auto-CRUD (Tier A) or custom screens (Tier B)?
- **Integrations:** Webhooks, external APIs, AI tools?
- **Edge cases:** Deletes, multitenancy, audit expectations.

Use Ask / Plan mode in the IDE when requirements are ambiguous.

### 2. Spec (write)

Update **before** implementation (template: `docs/modules-spec-template.md`):

| Artifact | When |
|---|---|
| `modules/<mod>/docs/spec.md` | New or changed module domain |
| `docs/23-tree-spec-framework.md` | Backend framework checkbox |
| `docs/24-tree-spec-admin-ui.md` | Admin UI checkbox |
| ADR in `docs/adr/` | New dependency or architecture choice |
| Matching `docs/NN-*.md` chapter | User-visible behaviour change |

Module spec template sections:

1. Purpose and personas  
2. Process flow (numbered steps)  
3. Models and fields  
4. RBAC matrix sketch  
5. Views (list/form/kanban/custom)  
6. Integrations and events  
7. Out of scope  

### 3. Implement (one-shot from spec)

Implementation order for a **new module**:

1. `manifest.py`, `model/domain.py`, `mapping.py`, `schemas.py`
2. `security/access.yaml`, `bootstrap.py` if seeds needed
3. `view/*.xml` for list/form when generic UI suffices
4. `actions.py`, optional `ai.py`
5. Tests under `backend/tests/` or repo `tests/`
6. Tier B UI only when spec marks views as custom

**Do not** invent libraries outside `pre-prompt.md` §3 without ADR.

### 4. Verify (same PR)

- [ ] At least one test covers new behaviour (`docs/20-testing.md`)
- [ ] Docs updated in same PR (same rule as code)
- [ ] `scripts/check_docs.py` green if doc map changed
- [ ] Manual smoke: list → create → edit → delete (or Playwright)

## Prompt-to-production tips

- Point the agent at **`docs/pre-prompt.md`** first, then module spec.
- Keep specs **short and testable** — agents one-shot better from
  checklists than prose essays.
- Prefer **Tier A** until UX proof demands Tier B (see ADR-0021).
- After Tier A works, add TanStack Query prefetch/expand before bespoke
  React pages.

## Anti-patterns

- Coding a module without `docs/spec.md`
- Hardcoded CRM pages instead of catch-all routes (removed in v1.0)
- Cross-module Python imports
- Skipping RBAC YAML
- Changing README locked hero tagline without product-owner approval

## References

- `docs/pre-prompt.md`
- `docs/01-engine-positioning.md`
- ADR-0021
- `docs/40-reference-product-caltrain.md`
