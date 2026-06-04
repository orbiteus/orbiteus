# Architectural Decision Records (ADRs)

Immutable records of binding architectural choices. Once an ADR is **Accepted**,
the decision is locked. Changes happen via a **new** ADR that declares
`Supersedes: NNNN`.

## Template

Use the structure in [`_template.md`](./_template.md) for new ADRs.

## Index

| # | Title | Status |
|---|---|---|
| 0001 | [Engine vs Framework vs Product positioning](./0001-engine-vs-framework.md) | Accepted |
| 0002 | [Mantine as the only design system](./0002-mantine-as-design-system.md) | Accepted |
| 0003 | [RBAC cache on Redis](./0003-rbac-cache-on-redis.md) | Accepted |
| 0004 | [BYOK AI credentials with Fernet](./0004-byok-ai-credentials.md) | Accepted |
| 0005 | [pgvector for embeddings](./0005-pgvector-for-embeddings.md) | Accepted |
| 0006 | [Realtime default: SSE](./0006-realtime-default-sse.md) | Accepted |
| 0007 | [Portal as a separate Next.js app](./0007-portal-as-separate-next-app.md) | Accepted |
| 0008 | [CRM-MVP rename: Person / Lead / Stage / Team](./0008-crm-mvp-rename-person-lead-stage-team.md) | Accepted |
| 0009 | [Anthropic + OpenAI + Ollama as MVP AI providers](./0009-anthropic-openai-ollama-providers.md) | Accepted |
| 0023 | [Gemini as fourth BYOK chat provider](./0023-gemini-provider.md) | Accepted |
| 0010 | [Postgres Outbox + EventBus for side effects](./0010-eventbus-postgres-outbox.md) | Accepted |
| 0011 | [Gunicorn + UvicornWorker as production HTTP server](./0011-gunicorn-uvicorn-workers.md) | Accepted |
| 0012 | [PgBouncer in front of Postgres](./0012-pgbouncer-in-front-of-postgres.md) | Accepted |
| 0013 | [Celery 5 instead of arq / dramatiq / RQ](./0013-celery-instead-of-arq.md) | Accepted |
| 0014 | [Redis Pub/Sub as realtime backplane](./0014-redis-pubsub-as-realtime-backplane.md) | Accepted |
| 0015 | [No Temporal in MVP](./0015-no-temporal-in-mvp.md) | Accepted |
| 0016 | [npm workspaces with packages/ui](./0016-npm-workspaces-with-packages-ui.md) | Superseded |
| 0017 | [httpOnly cookie session for the Admin UI (no FOAC)](./0017-httponly-cookie-session.md) | Accepted |
| 0018 | [AI agent primitive (`base.agent` + `base.agent-run`)](./0018-ai-agent-primitive.md) | Accepted |
| 0019 | [Agent delegation and scheduled runs](./0019-agent-delegation-and-scheduling.md) | Accepted |
| 0020 | [TanStack Query for admin-ui data layer](./0020-tanstack-query-admin-ui.md) | Accepted |
| 0021 | [Domain-first positioning and hybrid UI](./0021-domain-apps-and-repositioning.md) | Accepted |
