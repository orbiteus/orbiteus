# 15 — AI Layer

The AI layer is a first-class engine concern. Drop in a token, pick a provider,
ship.

## Components

```
orbiteus_core/ai/
  action.py            # Action dataclass (Command Palette + AI tool)
  registry.py          # ActionRegistry + AIRegistry (per-module configs)
  resolver.py          # RapidFuzz scoring for ⌘K
  router.py            # /api/ai/{actions, chat, dashboard, tools, embed, credentials}
  providers/
    base.py            # Provider ABC
    anthropic.py       # default
    openai.py          # secondary
    gemini.py          # Google Gemini API
    ollama.py          # optional local fallback
  keys.py              # base_ai_credentials CRUD + Fernet encryption
  context.py           # AIContextBuilder (RBAC-scoped data view)
  tools.py             # Action → tool, model → QueryTool, semantic_search
  prompts.py           # PromptTemplate registry
  embeddings.py        # pgvector helpers
  dashboard.py         # NL → aggregate query → chart spec
  budget.py            # token quota per tenant
  loop.py              # AgentLoop — multi-turn tool execution
  executor.py          # AgentExecutor — run base.agent definitions
  query_executor.py    # read_* tool → BaseRepository.search
```

## Agent primitive (ADR-0018)

Framework tables in `modules/base`:

- **`base.agent`** — slug, persona, module scope, allowed models/actions.
- **`base.agent-run`** — execution ledger (status, output, tool trace).

Runtime: `AgentLoop` executes tools across multiple provider turns;
`AgentExecutor` loads an agent definition under the caller's RBAC.
`run_agent_loop_stream()` powers streaming chat. Delegation via
`delegate_agent` tool (ADR-0019). Scheduled runs via Celery Beat.

Full spec: `docs/37-ai-agents.md`, ADR-0018, ADR-0019.

## Providers

| Provider | Status | Use case |
|---|---|---|
| Anthropic (Claude) | default | Primary chat + tool calling |
| OpenAI | secondary | Fallback or per-tenant preference |
| Ollama | optional | Local / air-gapped deployments only |

New providers require an ADR. The provider abstraction (`Provider` ABC) exposes:

```python
class Provider(ABC):
    async def chat(self, messages, tools=None, model=None, **opts) -> ChatResult
    async def embed(self, texts: list[str], model=None) -> list[list[float]]
    async def ping(self) -> bool
```

## BYOK (Bring Your Own Key)

```sql
CREATE TABLE base_ai_credentials (
    id              UUID PRIMARY KEY,
    tenant_id       UUID NOT NULL,
    provider        TEXT NOT NULL,            -- anthropic | openai | gemini | ollama
    secret_encrypted BYTEA NOT NULL,          -- Fernet(AI_SECRET_KEY)
    model_default   TEXT,                     -- e.g. "claude-3-7-sonnet"
    is_active       BOOLEAN NOT NULL DEFAULT true,
    monthly_token_budget BIGINT,              -- NULL = unlimited
    usage_tokens    BIGINT NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, provider)
);
```

- Encryption key (`AI_SECRET_KEY`) lives in env, never in DB. It must be a **valid Fernet key** (e.g. output of `Fernet.generate_key().decode()`). Development placeholders that are not valid Fernet material are **rejected** at runtime with a clear error — not passed through to `cryptography` as-is.
- API:
  - `POST /api/ai/credentials { provider, secret, model_default }` — store + ping
  - `GET /api/ai/credentials` — list (without secrets)
  - `DELETE /api/ai/credentials/{provider}`
- The engine ships ready-to-go: with no credential, the chat API returns
  `412 Precondition Required` and points the user to the credential UI.

## RBAC-scoped context

`AIContextBuilder` produces what the AI can see, derived from the human's
`RequestContext`:

```python
ctx = AIContextBuilder.build(
    request_ctx=current_user_ctx,
    module_config=ai_registry.get("crm"),  # AIModuleConfig from modules/crm/ai.py
)
# ctx.tools  -> [Tool(name="crm.lead.create", ...), QueryTool("crm.lead", filters=...)]
# ctx.system_prompt = ai_module_config.system_prompt
```

The user's RBAC is the upper bound. AI cannot widen scope by claiming roles.

## Tools

Three sources, all callable through provider function-calling:

1. **Actions** — every registered Action becomes a tool. Calls go through
   `ActionExecutor`, which invokes the underlying API endpoint.
2. **QueryTool per model** — `read_<model>(domain, fields, limit)` for every
   model in `accessible_models`. Calls go through `BaseRepository.search()`.
3. **`semantic_search(model, query, top_k)`** — pgvector lookup.

All tool calls are audited (`actor=ai`, `tool_name`, `args`, `result_status`).

## Embeddings (pgvector)

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE base_embeddings (
    id           UUID PRIMARY KEY,
    tenant_id    UUID NOT NULL,
    model        TEXT NOT NULL,
    record_id    UUID NOT NULL,
    provider     TEXT NOT NULL,
    model_name   TEXT NOT NULL,
    dim          INT  NOT NULL,
    vector       VECTOR(1536),         -- adjust per default provider; multiple columns possible
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, model, record_id, provider, model_name)
);
CREATE INDEX ON base_embeddings USING hnsw (vector vector_cosine_ops);
```

Refresh trigger: `record.created` / `record.updated` events for models listed
in module's `embed_models` produce Outbox entries; a Celery worker rate-limits
re-indexing per tenant.

## Dashboards

```
POST /api/ai/dashboard
{ "scope": "module:crm", "prompt": "weekly revenue by stage" }
→ 200
{
  "title": "Weekly revenue by stage",
  "chart_type": "bar",
  "x_axis": "stage_name",
  "y_axis": "sum_expected_revenue",
  "data": [ ... ]   // from /api/base/aggregate
}
```

The AI is given `aggregate(model, measure, group_by, filter)` as its only
tool when generating dashboards. Output is pure JSON (chart spec); the
front-end renders with recharts.

## Budget guard

- `monthly_token_budget` per tenant.
- Counter in Redis (`ai:budget:tenant:{id}:{yyyymm}`).
- Hitting the budget returns `429 AI Budget Exceeded` until next month.
- Budget breach also raises an Action visible to tenant admins.

## What AI cannot do

- Bypass RBAC.
- Call provider SDKs directly from a module (always through `providers/`).
- Read across tenants.
- Persist provider keys in code, env files, or audit logs.
- Run with elevated permissions in cron jobs (use `actor=system` with
  explicit RBAC scope).

## Configuration entry point

`POST /api/ai/credentials` with provider + secret = engine is on. That's the
"few prompts to plug AI into your HR module" experience: the framework already
ships the AI layer, the module declares `ai.py`, the front-end embeds
`<PromptInput>`.
