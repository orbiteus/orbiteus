# Orbiteus Documentation

> **AI agents must read [`pre-prompt.md`](./pre-prompt.md) before any other file in this folder.**

Orbiteus is an **AI-native engine** for building business applications and
internal AI agents. This folder is the source of truth for architecture,
conventions, and decisions.

## How to read these docs

1. **Start here:** [`pre-prompt.md`](./pre-prompt.md) — master context for humans and AI.
2. **Definitions:** [`glossary.md`](./glossary.md) — every term used elsewhere.
3. **Read in numeric order** if you are new — chapters build on each other.
4. **For trade-off rationales,** open [`adr/`](./adr/) — every binding decision
   has an immutable record.

## Reading order

| # | File | Topic |
|---|---|---|
| 00 | [`pre-prompt.md`](./pre-prompt.md) | Master context for AI agents |
| 00 | [`glossary.md`](./glossary.md) | Definitions |
| 01 | [`01-engine-positioning.md`](./01-engine-positioning.md) | Engine ⟷ Framework ⟷ Product |
| 02 | [`02-architecture.md`](./02-architecture.md) | Three layers, modular monolith, lifecycle |
| 03 | [`03-modules.md`](./03-modules.md) | Module convention |
| 04 | [`04-data-model.md`](./04-data-model.md) | BaseModel, SystemModel, base engine tables, custom fields |
| 05 | [`05-rbac-multitenancy.md`](./05-rbac-multitenancy.md) | RBAC levels and tenant isolation |
| 06 | [`06-auth.md`](./06-auth.md) | JWT, refresh rotation, 2FA, share links |
| 07 | [`07-api.md`](./07-api.md) | Auto-CRUD, query operators, OpenAPI, webhooks |
| 08 | [`08-admin-ui.md`](./08-admin-ui.md) | Dynamic renderer, widget registry, ⌘K |
| 09 | [`09-portal-ui.md`](./09-portal-ui.md) | External partner portal |
| 10 | [`10-design-system.md`](./10-design-system.md) | Mantine 9, `orbiteus-ui`, branding |
| 11 | [`11-realtime.md`](./11-realtime.md) | SSE + Redis Pub/Sub backplane |
| 12 | [`12-events-and-queues.md`](./12-events-and-queues.md) | EventBus + Outbox + Celery |
| 13 | [`13-cache.md`](./13-cache.md) | Redis usage map and TTLs |
| 14 | [`14-audit.md`](./14-audit.md) | Mandatory 100% audit policy |
| 15 | [`15-ai-layer.md`](./15-ai-layer.md) | Providers, BYOK, tools, embeddings, budget |
| 16 | [`16-ai-recipes.md`](./16-ai-recipes.md) | How to plug AI into a module |
| 37 | [`37-ai-agents.md`](./37-ai-agents.md) | Agent definitions, runs, AgentLoop |
| 17 | [`17-deployment.md`](./17-deployment.md) | Docker compose dev / prod, nginx, certbot |
| 18 | [`18-security.md`](./18-security.md) | Secrets, CSP/CORS, threat model |
| 19 | [`19-i18n.md`](./19-i18n.md) | Locale strategy and catalogs |
| 20 | [`20-testing.md`](./20-testing.md) | Pytest, Vitest, Playwright, fixtures |
| 21 | [`21-release-and-versioning.md`](./21-release-and-versioning.md) | Semver, changelog, alembic policy |
| 22 | [`22-implementation-plan.md`](./22-implementation-plan.md) | Phases and waves |
| 23 | [`23-tree-spec-framework.md`](./23-tree-spec-framework.md) | Backend [x]/[ ] tree |
| 24 | [`24-tree-spec-admin-ui.md`](./24-tree-spec-admin-ui.md) | Admin UI [x]/[ ] tree |
| 25 | [`25-tree-spec-portal-ui.md`](./25-tree-spec-portal-ui.md) | Portal UI [x]/[ ] tree |
| 26 | [`26-canonical-crm.md`](./26-canonical-crm.md) | Canonical CRM: Person / Lead / Stage / Team |
| 27 | [`27-licenses.md`](./27-licenses.md) | License policy |
| 28 | [`28-open-questions.md`](./28-open-questions.md) | Questions awaiting ADR |
| 29 | [`29-observability.md`](./29-observability.md) | Logs, metrics, traces |
| 30 | [`30-rate-limiting.md`](./30-rate-limiting.md) | Token bucket per tenant/user/IP |
| 31 | [`31-backups-and-dr.md`](./31-backups-and-dr.md) | pg_dump, retention, RPO/RTO |
| 32 | [`32-multi-host-migration.md`](./32-multi-host-migration.md) | When to leave compose |
| 33 | [`33-data-retention-and-gdpr.md`](./33-data-retention-and-gdpr.md) | Audit retention, anonymization, DSAR |
| 34 | [`34-inventory-and-status.md`](./34-inventory-and-status.md) | Code vs docs honest snapshot |
| 35 | [`35-core-definition-of-done.md`](./35-core-definition-of-done.md) | What "v1.0" means |
| 36 | [`36-development-plan.md`](./36-development-plan.md) | Step-by-step PR plan to v1.0 |
| 39 | [`39-spec-driven-agent-workflow.md`](./39-spec-driven-agent-workflow.md) | Ask → Spec → Implement → Verify |
| 40 | [`40-reference-product-caltrain.md`](./40-reference-product-caltrain.md) | Reference domain app (LadiesGym) |
|    | [`modules-spec-template.md`](./modules-spec-template.md) | Copy-paste module spec skeleton |
|    | [`adr/`](./adr/) | Architectural Decision Records |

## Conventions

- **English only** in code, identifiers, comments, file names, and docs.
  UI strings can be translated through message catalogs (see `19-i18n.md`).
- **One topic per file** — if a doc grows beyond ~250 lines, split it.
- **ADRs are immutable** once accepted. Changes happen via a new ADR that
  declares `Supersedes: NNNN`.
- **Every claim is testable.** When a doc states a rule, the matching test or
  CI check should exist (see `scripts/check_docs.py`).
