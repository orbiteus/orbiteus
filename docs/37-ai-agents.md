# 37 — AI Agents (framework primitive)

Named, tenant-configurable AI agents, multi-turn tool execution, delegation,
scheduling, and an execution ledger. This chapter describes **engine
infrastructure** — not a product feature. The canonical CRM module ships
showcase agents as a **developer tutorial**.

See ADR-0018 (primitives) and ADR-0019 (delegation, scheduling, streaming).

## Layering

| Layer | Responsibility |
|---|---|
| `orbiteus_core/ai/` | Provider calls, AgentLoop, delegation, executor, budget, audit |
| `modules/base` | `base.agent`, `base.agent-run` models + seed |
| `modules/<product>/ai.py` | Declares which models/actions exist for AI |
| `modules/crm` | Canonical example — seeds `crm-assistant` + `crm-analyst` |

## Data model

### `base.agent`

| Field | Type | Notes |
|---|---|---|
| `slug` | str | Unique per tenant, e.g. `crm-assistant` |
| `name` | str | Display name |
| `module_scope` | str | Module name (`crm`) or `*` |
| `system_prompt` | text | Persona and rules |
| `allowed_models` | JSONB[str] | Subset of `AIModuleConfig.accessible_models` |
| `allowed_actions` | JSONB[str] | Subset of `AIModuleConfig.callable_actions` |
| `provider` | str | Optional BYOK provider override |
| `model_default` | str | Optional model override |
| `can_delegate` | bool | Enables `delegate_agent` tool |
| `allowed_delegate_slugs` | JSONB[str] | Target slugs; empty = any except self |
| `schedule_interval_minutes` | int | Null = no schedule |
| `schedule_prompt` | text | Prompt for scheduled runs |
| `schedule_last_run_at` | timestamptz | Updated by scheduler |
| `is_active` | bool | Inactive agents reject runs |
| `is_system` | bool | Seeded showcase — cannot delete |

### `base.agent-run`

| Field | Type | Notes |
|---|---|---|
| `agent_id` | UUID FK | → `base_agents.id` |
| `parent_run_id` | UUID FK | → parent run when delegated |
| `depth` | int | 0 = root; max 3 (ADR-0019) |
| `triggered_by_user_id` | UUID | Who started the run |
| `input_prompt` | text | User/task prompt |
| `status` | enum | `pending` \| `running` \| `completed` \| `failed` |
| `output_text` | text | Final assistant reply |
| `tool_trace` | JSONB | Compact step log |
| `tokens_used` | int | Aggregated usage |
| `error_message` | text | Set when `status=failed` |

## Runtime

### AgentLoop

Multi-turn executor in `orbiteus_core/ai/loop.py`:

- Executes `read_*`, action tools, `semantic_search`, and `delegate_agent`.
- Non-streaming: `run_agent_loop()`.
- Streaming: `run_agent_loop_stream()` — SSE events `text`, `tool_call`,
  `tool_result`, `done`.

### Delegation (`delegate_agent` tool)

When `can_delegate=true`, the agent may call:

```json
{ "agent_slug": "crm-analyst", "prompt": "Summarize hot leads" }
```

The engine creates a child `base.agent-run` with `parent_run_id` and runs it
synchronously under the same `RequestContext`. Maximum depth: **3**.

### Scheduling

Celery Beat runs `tasks.ai_tasks.poll_scheduled_agents` every 5 minutes.
Agents with `schedule_interval_minutes` set and elapsed interval execute
`schedule_prompt` automatically.

### Tool scoping

1. Module declares surface in `ai.py` (L1).
2. Agent allow-lists filter that surface (L2).
3. `RequestContext` of the human user is the upper bound (L0 RBAC).

## HTTP API

| Method | Path | Purpose |
|---|---|---|
| CRUD | `/api/base/agent` | Manage definitions |
| GET | `/api/base/agent-run` | List run history |
| POST | `/api/ai/runs` | Start run — `{ agent_id, prompt, async?, parent_run_id?, depth? }` |
| GET | `/api/ai/runs/{id}` | Run status + output |
| POST | `/api/ai/chat?stream=1` | Multi-turn streaming chat with tool execution |

Async runs: Celery `tasks.ai_tasks.run_agent_run`.

### Realtime (SSE)

Subscribe to:

- `tenant:{tenant_id}:model:base.agent-run:record:{run_id}`
- `tenant:{tenant_id}:model:base.agent-run:list`

Events: `agent_run.updated` with `{ status, output_text, tokens_used }`.

## Admin UI

Sidebar **AI**:

- AI Integration (BYOK)
- Agent Console → `/technical/agent-console` (async runs + SSE)
- Agents → `/base/agent`
- Agent runs → `/base/agent-run`

Global **Assistant** drawer (⌘ header sparkle icon) uses streaming `/api/ai/chat?stream=1`.
Record forms embed `<PromptInput scope="module:{module}" stream />` (framework hook).
CRM appears under its module label in the dynamic sidebar section.

## Developer path

1. Add `ai.py` to your module (`16-ai-recipes.md`).
2. Register action handlers with `register_handler()`.
3. Configure BYOK → AI → AI Integration.
4. Create agents (or copy showcase seeds).
5. Enable delegation / schedule on agent form fields.
6. Run via API or Agent runs list; subscribe to SSE for async status.

## Showcase (batteries included)

| Asset | Purpose |
|---|---|
| `crm-analyst` | Read-only CRM agent (delegation target) |
| `crm-assistant` | Full CRM agent with delegation to analyst |
| CRM `ai.py` | Module AI surface |
| `<PromptInput>` on forms | Live module-scoped chat |

## Tests

- `backend/tests/test_ai_tool_loop.py` — loop, scoping, streaming unit tests
- `backend/tests/test_ai_agents.py` — CRUD, runs, mocked execution
- `backend/tests/test_ai_delegation.py` — delegation depth and slug allow-list

## Related

- Portal-scoped agent triggers follow ADR-0007 when portal auth ships.
- Outbox-driven embedding refresh: `orbiteus_core/embedding_dispatcher.py`, `embedding_refresh.py`, `tasks/embedding_tasks.py`.
