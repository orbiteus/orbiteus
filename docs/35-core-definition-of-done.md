# 35 — Core Definition of Done (v1.0 — engine published)

The engine is publishable as **v1.0** when **all** of the items below are
true. No exceptions, no "we'll add it later".

## 1. Boring infra runs with one command

- [ ] `docker compose --profile prod up -d --build` brings up:
      Postgres 16 + pgvector, PgBouncer, Redis 7, backend (Gunicorn +
      UvicornWorker), Celery worker, Celery Beat, admin-ui, portal-ui, nginx.
- [ ] `docker compose up` (default dev profile) brings up the dev stack
      (single replica, hot reload) on a fresh checkout in < 3 min.
- [ ] All services have liveness + readiness healthchecks.
- [ ] `migrate` is a separate one-shot service; backend depends on its success.
- [ ] nginx config supports SSE (`proxy_buffering off` on `/api/realtime/`).

## 2. Multi-tenant boundary is provable

- [ ] Every business model has `tenant_id`.
- [ ] Test: cross-tenant read attempt returns `403`/empty result.
- [ ] Test: cross-tenant write attempt is blocked at repository.
- [ ] RBAC cache lives in Redis; mutation invalidation works across replicas.

## 3. Auth is production-grade

- [ ] JWT access TTL = 15 min, refresh TTL = 7 days, refresh rotates on use.
- [ ] `jti` revocation list in Redis; logout effectively kills tokens.
- [ ] 2FA TOTP works end-to-end including recovery codes.
- [ ] Password reset over email (with single-use, time-bound link).
- [ ] Bootstrap admin password rotation enforced in production.
- [ ] Login is rate-limited per email + IP; tested.

## 4. Audit is mandatory and complete

- [ ] `base_audit_log` populated on every CRUD via `BaseRepository`.
- [ ] AI tool calls audited with `actor=ai`, `tool_name`, `args` (sanitized).
- [ ] Auth events (login success/fail) audited.
- [ ] Workflow transitions audited.
- [ ] Endpoint `GET /api/base/audit-log` paginated and RBAC-gated.
- [ ] Tests confirm `actor` semantics for user / ai / system.

## 5. Events and queues

- [ ] EventBus dispatches synchronous in-request hooks for audit, cache
      invalidation, and embeddings refresh signal.
- [ ] `base_outbox` is committed atomically with business writes.
- [ ] Celery worker drains the outbox idempotently with bounded retry +
      dead-letter status.
- [ ] Celery Beat reads `base_cron` and schedules tasks.
- [ ] Test: webhook delivered after a `record.updated` event.
- [ ] Test: a failing webhook reaches `dead_letter` after 10 retries.

## 6. Realtime works across replicas

- [ ] SSE endpoint `/api/realtime/subscribe` accepts multi-topic subscribe.
- [ ] Redis Pub/Sub is the cross-replica backplane.
- [ ] Topics are tenant-scoped; cross-tenant subscriptions return `403`.
- [ ] Test: two browsers see the same kanban move within < 500 ms.

## 7. Cache and rate limiting

- [ ] Redis hosts: RBAC cache, jti revocation, idempotency keys, rate limit
      buckets, AI budget counters, presence sets.
- [ ] `429 Too Many Requests` returned with `Retry-After`.
- [ ] Tests for tenant + user + IP buckets.

## 8. AI layer is plug-and-play (BYOK)

- [ ] `base_ai_credential` table with Fernet at-rest encryption.
- [ ] `POST /api/ai/credentials` validates by ping; `GET` lists without secrets.
- [ ] Provider adapters: Anthropic (default), OpenAI, Ollama. ABC stable.
- [ ] `AIModuleConfig` registry populated from each module's `ai.py`.
- [ ] AI tools: Action, QueryTool per model, `semantic_search`.
- [ ] AI runs only with the user's RBAC; never elevated.
- [ ] `pgvector` `base_embedding` table + HNSW index; refresh via Outbox.
- [ ] `/api/ai/chat` (streaming, tool calling), `/api/ai/dashboard` (NL → chart).
- [ ] Budget guard returns `429 AI Budget Exceeded` with reset hint.
- [ ] PII redaction pipeline before remote provider calls.
- [ ] Test: AI tool call moves a CRM lead's stage and audits with `actor=ai`.

## 9. Admin UI is a renderer (zero TSX per module)

- [ ] All hardcoded `app/{crm,base,technical}/*` pages removed.
- [ ] Catch-all routes cover list / form / kanban / calendar / graph.
- [ ] Widget registry covers: text, email, tel, number, textarea, boolean,
      date (+ locale display), select (static + dynamic), many2one (resolved),
      badge, monetary, statusbar, tags, readonly.
- [ ] Calendar view wired (`crm.lead.expected_close_date`).
- [ ] Graph view backed by `/api/base/aggregate`.
- [ ] Toasts on create/update/delete success and on 403/404/network errors.
- [ ] Empty states + loading skeletons on list / form / kanban.
- [ ] All tracked strings in English (no Polish leaks).
- [ ] `/welcome` (public) + `/login` (form only) + `/` (dashboard) split.

## 10. AI components in admin UI

- [ ] `<PromptInput>` available in the form view of any model.
- [ ] `<AIChatPanel>` available globally (drawer) and per-record (inline).
- [ ] `<AIDashboard>` renders chart specs returned by `/api/ai/dashboard`.
- [ ] Components live under `admin-ui/src/orbiteus-ui/` when both apps need the same UX; portal copies when adopted.
- [ ] Graceful fallback when no `base_ai_credential` is configured.

## 11. Canonical CRM (Person / Lead / Stage / Team)

- [ ] Models: `crm.person` (kind enum), `crm.lead`, `crm.stage`, `crm.team`.
- [ ] Old models removed; migration provided (expand → migrate → contract).
- [ ] Bootstrap moved to `modules/crm/bootstrap.py`; gone from `api.py`.
- [ ] Demo `actions.py` covers create / move stage / assign team / mark won/lost.
- [ ] Demo `ai.py` ships sensible suggested prompts and dashboard examples.
- [ ] List, kanban, calendar, form views all working without TSX.
- [ ] Realtime updates demonstrably work in CRM kanban.

## 12. Portal UI (external partner)

- [x] `portal-ui/` Next.js 16 app scaffolded.
- [ ] Share-link issuance endpoint (`POST /api/auth/share`) live.
- [ ] `/s/[token]` exchange flow working.
- [ ] `<portal>` view declaration parsed and respected (read-only by default).
- [ ] Portal user cannot read non-declared fields nor mutate non-declared actions.
- [ ] Realtime works for portal-scoped resources only.
- [ ] Negative tests: cross-tenant + non-declared model both `403`.

## 13. Observability + ops

- [ ] Structured JSON logs with `request_id`, `tenant_id`, `actor`, `route`, `latency_ms`.
- [ ] `/metrics` endpoint with the metric families listed in `29-observability.md`.
- [ ] OpenTelemetry tracing opt-in (`OTEL_EXPORTER_OTLP_ENDPOINT`).
- [ ] Backups: nightly `pg_dump` to S3-compatible storage with documented restore.
- [ ] Restore drill executed at least once and timed in the runbook.

## 14. Documentation reflects reality

- [ ] `scripts/check_docs.py` green.
- [ ] `tests/test_docs.py` green.
- [ ] `docs/34-inventory-and-status.md` updated to match the v1.0 state
      (everything DONE).
- [ ] CHANGELOG includes a v1.0 release note section with migration steps.
- [ ] README.md (root) reflects the engine's value proposition and points
      to `docs/pre-prompt.md`.

## 15. Tests + CI gate every merge

- [ ] Backend coverage: `orbiteus_core ≥ 90%`, `base ≥ 85%`, `auth ≥ 85%`,
      `crm ≥ 80%`.
- [ ] Frontend Vitest setup + tests for each widget.
- [ ] At least 5 Playwright E2E scenarios green (login, create, kanban move,
      realtime cross-browser, AI prompt with mocked provider).
- [ ] CI runs: `check_docs.py`, backend pytest, frontend Vitest, Playwright,
      docs link-check, `pip-audit`, `npm audit`, license check.

## 16. Security gates

- [ ] Production refuses to start with default `SECRET_KEY` or
      `BOOTSTRAP_ADMIN_PASSWORD`.
- [ ] All endpoints validated by Pydantic; no unvalidated request payloads.
- [ ] CSP, HSTS, frame-ancestors, referrer policy in production nginx config.
- [ ] No GPL deps; license report committed.
- [ ] Pre-commit hook with `detect-secrets`.

---

**Until every box above is ticked, the engine is not v1.0.**

Sub-versions (v0.x) ship freely as long as documentation and tests stay
honest. Public release waits for v1.0.
