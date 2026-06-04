# ADR-0018: AI agent primitive (`base.agent` + `base.agent-run`)

- **Status:** Accepted
- **Date:** 2026-05-28
- **Context tags:** backend, ai, framework

## Context

Orbiteus ships a first-class AI layer (BYOK, providers, tools, embeddings) and
per-module `AIModuleConfig` declarations. Developers can chat and call tools
through `/api/ai/chat`, but there is no **named, reusable agent definition**
that operators can configure without code changes, and no **run ledger** for async
executions.

The engine must stay a **framework**, not a product: agent infrastructure belongs
in `modules/base` and `orbiteus_core/ai`. The canonical CRM module demonstrates
usage via a seeded showcase agent — it does not own agent runtime code.

Multi-agent delegation, scheduled runs, and streaming multi-turn loops are
specified in ADR-0019 and implemented in the same release wave as this ADR.

## Decision

1. Add two framework tables in `modules/base`:
   - **`base_agents`** — tenant-scoped agent definitions (slug, persona,
     module scope, allowed models/actions, optional provider override).
   - **`base_agent_runs`** — execution ledger (prompt, status, output, tool trace,
     token usage).

2. Add engine runtime in `orbiteus_core/ai/`:
   - **`AgentLoop`** — multi-turn provider chat that executes read tools, action
     tools, and `semantic_search` until the model stops calling tools or a turn
     cap is reached.
   - **`AgentExecutor`** — loads an agent definition, scopes tools to its
     allow-lists, runs `AgentLoop` under the caller's `RequestContext`.

3. Expose HTTP:
   - Schema-driven CRUD for agents and run history via auto-CRUD
     (`/api/base/agent`, `/api/base/agent-run`).
   - `POST /api/ai/runs` to start a run (sync or async via Celery).
   - `GET /api/ai/runs/{id}` for run status.

4. Seed one **system showcase agent** (`crm-assistant`) per default tenant to
   guide developers. CRM remains the canonical example module; the agent is
   framework configuration, not CRM product logic.

5. Admin UI:
   - **AI** sidebar section: AI Integration, Agents, Agent runs.
   - Dynamic CRUD pages — no per-agent TSX.
   - Generic `<PromptInput scope="module:{name}">` on record forms when the
     module exposes `AIModuleConfig`.

## Consequences

- Developers define AI surface in `ai.py`, then create agents in admin or via API.
- RBAC upper bound unchanged: agent allow-lists are subsets of module declarations.
- Every tool step is audited (`actor=ai`, optional `agent_run_id` in metadata).
- Async runs require Celery worker; sync runs suit admin "test run" flows.
- Delegation, scheduling, and streaming loops: ADR-0019.

## Alternatives considered

- **LangGraph / Temporal for orchestration** — rejected for MVP (ADR-0015).
- **Agents as JSON in `base.config-param`** — no typed CRUD, no run ledger.
- **Product-specific agents in CRM module** — violates engine boundary; CRM only
  seeds a demo definition.

## References

- `docs/37-ai-agents.md`
- `docs/15-ai-layer.md`
- `docs/26-canonical-crm.md`
- ADR-0004, ADR-0005, ADR-0009, ADR-0013, ADR-0015
