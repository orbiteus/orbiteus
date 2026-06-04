# Glossary

> Definitions that the rest of the docs and the codebase rely on.
> If a term is missing here, add it before using it elsewhere.

| Term | Definition |
|---|---|
| **Engine** | A semi-framework / semi-product hybrid: framework primitives + opinionated batteries (auth, RBAC, audit, realtime, AI) + one canonical product example (CRM-MVP). Orbiteus is an engine. |
| **Framework layer** | Code that implements infrastructure primitives — `orbiteus_core`, `modules/base`, `modules/auth`. No business logic. |
| **Product layer** | Code that implements business logic on top of the framework — `modules/crm`, `modules/hr`, etc. |
| **Canonical example** | The minimal product module shipped in the engine to demonstrate capabilities. Currently CRM-MVP (Person, Lead, Stage, Team). |
| **Module** | A self-contained directory under `backend/modules/<name>/` declared in `manifest.py`. See `03-modules.md`. |
| **Tenant** | A top-level isolation unit. Every business record carries `tenant_id`. Tenants do not see each other's data. |
| **Company** | A legal entity within a tenant. Optional secondary segmentation. |
| **Scope** (auth) | A claim on a JWT: `internal` for admin UI, `portal` for partner portal, `ai` for AI-driven calls (always derived from a user scope). |
| **RequestContext** | The runtime object that carries `tenant_id`, `company_id`, `user_id`, `roles`, `is_superadmin`, `scope` — the upper bound on what a request (or AI tool) can do. |
| **BaseRepository** | The mandatory data access layer. Enforces tenant isolation, RBAC, audit. AI tools call the same repository as humans. |
| **Action** | A declarative business operation registered by a module. Backs the Command Palette and acts as an AI tool. See `15-ai-layer.md`. |
| **AI Tool** | Anything callable by an AI provider's function-calling API. Sources: registered Actions, per-model `QueryTool`, `semantic_search`. |
| **AIModuleConfig** | The `ai.py` declaration in a module. Lists `accessible_models`, `callable_actions`, `suggested_prompts`, system prompt overrides. |
| **Agent** | A tenant-scoped named AI persona (`base.agent`) with scoped tools and system prompt. Configured in admin or API; executed by `AgentExecutor`. |
| **Agent run** | One execution of an agent (`base.agent-run`): prompt in, tool loop, text out. Sync via API or async via Celery. |
| **AgentLoop** | Engine multi-turn chat loop that executes read/action/semantic tools until the model finishes or hits a turn cap. |
| **BYOK** | "Bring Your Own Key": tenants supply their own provider API tokens; engine never ships shared keys. |
| **EventBus** | In-process publish/subscribe within a single request lifecycle. Used for synchronous hooks (audit, cache invalidation, embeddings refresh). |
| **Outbox** | The `base_outbox` table that persists side-effect intents atomically with the business transaction. Drained by Celery workers with idempotent retry. |
| **Realtime topic** | A Pub/Sub channel of the form `tenant:{id}:model:{m}:record:{id}` for SSE fan-out. |
| **Audit log** | Mandatory `base_audit_log` row for every CRUD operation: actor, request_id, tenant_id, before/after diff. Opt-out only for system log tables. |
| **ui-config** | The metadata document at `GET /api/base/ui-config` that the admin UI consumes to render lists, forms, kanbans, calendars, and command palette entries — without per-module TSX. |
| **Widget** | A frontend component registered for a field type or attribute (text, email, badge, monetary, statusbar, many2one, ...). Forms and lists render through the widget registry only. |
| **Command Palette** | The ⌘K modal that searches Actions via RapidFuzz. Deterministic, no LLM in the happy path. Distinct from `<PromptInput>` (generative AI chat). |
| **Share link** | A signed, time-bound URL that grants a portal scope to an external user, restricted to specific resources. |
| **Canonical example** | See "Canonical example" above. |
| **ADR** | Architectural Decision Record. Immutable Markdown file in `docs/adr/` documenting a binding choice and its trade-offs. |
| **Boring tech** | Technology that is widely used in production, ≥ 5 years mature, well documented, and well known to senior engineers and AI assistants. The MVP stack is intentionally boring. |
