# Changelog

All notable changes to Orbiteus are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning follows [SemVer](https://semver.org/spec/v2.0.0.html).

> **Note on the existing `v1.0.0` git tag.** A `v1.0.0` tag was pushed
> on 2026-05-03 against the engine snapshot below. With the framework
> Definition of Done at ~92 % of its checkboxes (see
> `docs/34-inventory-and-status.md`), the publishable version is
> `v1.0.0-rc1`. The `v1.0.0` tag remains pinned to that earlier commit
> for archival purposes; the `v1.0.0` GA tag waits for the four
> follow-ups documented in the inventory.

## [Unreleased]

## [1.1.1] — 2026-05-30

### Fixed

- **Admin dashboard crash after login (React #185).** `AppShellLayout` seeded
  default sidebar expansion on every `navSections` change without persisting to
  `localStorage`, causing an infinite update loop on fresh sessions (demo /
  incognito). Defaults are now written once via
  `initializeExpandedSectionsIfAbsent()`.

### Changed

- **Demo compose (`docker-compose.demo.yml`):** Postgres image
  `pgvector/pgvector:pg16` (migrations require `vector`); added `redis` service
  and `REDIS_URL` for RBAC cache invalidation.
- **Edge proxy:** unauthenticated `GET /` redirects to `/welcome` (not
  `/login?next=/`).
- **Public routes:** login/welcome links use hard navigation
  (`PublicNavLink` / `PublicNavButton`) to avoid App Router client transitions
  stalling on public pages.


### Added

- **UI i18n as module catalogs (ADR-0023).** Canonical English in
  `modules/base/i18n/en.json`; optional `modules/locales` ships `pl`, `de`,
  `fr`. API: `GET /api/base/i18n/locales`, `GET /api/base/i18n/messages/{lang}`.
  `@orbiteus/i18n` package; `scripts/check_i18n.py` and
  `scripts/sync_public_i18n_fallbacks.py` in CI.
- **Module catalog toggles** (`module.<name>.enabled`) with admin UI invalidation
  for ui-config, i18n, resources, and attachments.
- **Locales technical page**, languages metadata (`source` / `module`), DB overrides
  via `base.ui-translation`.
- **AI agents** (definitions, runs, delegation, Agent Console), Gemini provider
  (ADR-0023), system status probes, attachment filestore, mail settings UI.
- **TanStack Query** across admin-ui (ADR-0020); JSON list/form views; expanded
  sidebar navigation and module runtime refresh without full reload.
- **Reference domain repositioning (ADR-0021):** canonical in-repo CRM module
  removed; Caltrain/LadiesGym documented as reference product.

### Changed

- **Admin UI performance:** no server-side full-catalog fetch in root layout;
  `/login` and `/welcome` use static public-page fallbacks (~145 keys); authenticated
  shell loads API catalog once with 5 min React Query cache; module `enabled_map`
  and merged message caches on backend.
- **Docker dev:** `ensure-npm-deps.sh` skips repeat `npm install`; fixed
  `cd /app/admin-ui` in compose commands; portal i18n shell non-blocking bootstrap.

### Fixed

- Login/API errors when postgres/redis were down; proxy 503 with clear message.
- Module disable hiding locale packs from picker and API without process restart.
- Hydration and duplicate branding on welcome headers.

## [1.0.0-rc1] — 2026-05-04 (release candidate)

### Added — auth + access

- **HttpOnly cookie session for the Admin UI.** JWTs no longer travel
  through `localStorage`. Backend writes `orbiteus_token` (Path=`/`,
  15 min) and `orbiteus_refresh` (Path=`/api/auth`, 7 days) as
  `HttpOnly`, `SameSite=Lax` cookies; `Secure` is enabled automatically
  in production. The new Edge proxy at `admin-ui/src/proxy.ts` (Next 16
  successor of `middleware.ts`) redirects unauthenticated requests to
  `/login?next=<path>` *before* SSR runs, eliminating the Flash Of
  Authenticated Content. `Authorization: Bearer …` keeps working for
  non-browser clients (the `/api/auth/login` body still ships both
  tokens). See [ADR-0017](docs/adr/0017-httponly-cookie-session.md).
- **`POST /api/auth/logout`** — clears both auth cookies and revokes
  the current access `jti` in Redis. The Admin UI `Logout` menu item
  posts to it before redirecting to `/login`.
- **Password reset flow** — `POST /api/auth/password/{request,reset}`
  with always-200 responses on `request` (defeats user enumeration),
  per-email throttle, single-use JWT (TTL 30 min) revoked through the
  shared Redis `jti` list. Mailer in dev logs to stdout; production
  uses `aiosmtplib` with optional STARTTLS. New public pages
  `/forgot-password` and `/reset/[token]`.
- **Per-tenant + per-user rate-limit buckets.** The middleware now
  decodes the access token (cookie or `Authorization` header) and
  applies `rl:tenant:<tid>` (default 1000/min) and `rl:user:<uid>`
  (default 60/min) on top of the existing `rl:ip:<host>`.
- **`/welcome` split out from `/login`.** Marketing copy lives at the
  new public route; `/login` is sign-in only. Whitelisted in the proxy
  matcher so unauthenticated visitors can reach `/welcome`.

### Added — framework primitives

- **RBAC cache moved to Redis.** Two-tier cache: process-local L1 +
  Redis-backed L2 keyed by `rbac:access` / `rbac:rules` / `rbac:version`.
  Cross-replica invalidation over a `rbac.invalidate` Pub/Sub channel —
  any mutation of `base_model_access` / `base_rules` propagates within
  ~50 ms. Open-fail on Redis outage.
- **`GET /api/base/aggregate?model=&group_by=&op={count|sum|avg|min|max}&measure=`**
  framework primitive — single tenant-scoped endpoint that backs
  the Graph view and the AI dashboard. Reuses `apply_record_rules`
  so the data pipe through the same RBAC the repository layer uses.
- **`?expand=field1,field2` on every auto-CRUD list** — resolves
  many2one foreign keys to a sibling `<field>__name` cell using the
  first matching display column on the target table (`name |
  label | title | email | code`). Tenant-scoped + record-rule
  filtered.
- **AI streaming chat.** `POST /api/ai/chat?stream=1` returns
  `text/event-stream` with `event: text|tool_call|done|error`.
  Native streaming for Anthropic via `client.messages.stream(...)`;
  default fallback for OpenAI/Ollama emits the full reply as a
  single chunk + `done`.
- **Mail abstraction** in `orbiteus_core/mail.py` — single
  `send_mail(...)` coroutine with a dev-log fallback when
  `smtp_host=""` and a production `aiosmtplib` path. Used today by
  password reset; future template-driven mail will sit on top.
- **Audit-log helper** `orbiteus_core/audit.py` — central
  `write_audit(session, *, actor, operation, model, …)` with an
  actor allow-list (`user|ai|portal|system`) and `redact_payload`
  scrubbing. Wired into:
    - `actor=user`, `operation=login` / `login_failed` /
      `password_reset_requested` / `password_reset_completed` —
      from `auth/router.py`.
    - `actor=ai`, `operation=tool_call` — from every accepted
      `chat()` invocation in `ai/router.py`, including the
      streaming variant.

### Added — UI

- **MonetaryField widget** (`admin-ui/src/components/widgets/
  MonetaryField.tsx`) with `MonetaryCell` (list cells) and
  `MonetaryInput` (form input). Reads `currency_code` from the
  ui-config `FieldMeta`, falls back to `PLN`. Backend serves
  `currency_code` for every monetary field.
- **EmptyState + SkeletonRows** components wired into
  `ResourceList`, `ResourceKanban`, `ResourceCalendar`,
  `ResourceGraph`. Loading shows shape-preserving skeletons; empty
  shows an icon + headline + CTA. Search-aware copy on the list view.
- **Login form** gains a "Forgot password?" anchor.

### Added — portal

- **Portal-scoped realtime** — new `GET /api/portal/realtime?token=`
  share-token-authenticated SSE feed that reuses the same Redis
  Pub/Sub backplane as the admin shell. The portal-ui share page
  refreshes automatically when the underlying record changes.
- **Portal mutations + view declaration.** Exchange response carries
  `view_mode: "readonly"` (DoD §12.5 default) and
  `available_mutations: [...]` derived from share-token permissions.
  Frontend renders `CommentSurface` / `AttachmentSurface` only when
  the corresponding permission is granted; both are still
  permission-gated server-side in `_require_permission`.

### Added — observability + ops

- **Prometheus `/metrics` series expanded** to match
  `docs/29-observability.md`: DB query duration + pool-in-use gauge,
  Redis commands + latency, Celery task duration + outcomes + queue
  depth, Outbox pending/dead, AI calls + tokens + provider latency,
  SSE active connections, pubsub messages.
- **Backups** — `scripts/backup_db.sh` gains an optional `aws s3 cp`
  push (S3-compatible: AWS, B2, Wasabi, MinIO). New
  `scripts/restore_drill.sh` spins up a scratch Postgres, restores
  the latest backup, asserts the schema is healthy, and appends a
  log line. Cron file at `deploy/prod/cron/orbiteus-backups`
  schedules daily backup (02:00 UTC) and weekly drill (Sundays
  04:00 UTC). Drill executed on the dev stack — log evidence in
  `docs/31-backups-and-dr.md`.
- **CSP + tightened security headers** in
  `deploy/prod/nginx.conf` — Content-Security-Policy (allow-list of
  `'self'` everywhere, `frame-ancestors 'none'`, `unsafe-inline` only
  where Mantine + Next dev runtime require it),
  `X-Content-Type-Options nosniff`, explicit
  `Referrer-Policy strict-origin-when-cross-origin`. HSTS / X-Frame-
  Options were already present.
- **License audit + no-GPL gate** — new
  `scripts/generate_licenses.sh` produces
  `THIRD_PARTY_LICENSES.{python,node}.json` (committed) and audits
  via Python with an explicit dynamic-link / multi-license
  allow-list (`@img/sharp-libvips`, `psycopg2`, `psycopg2-binary`,
  `num2words`, `docutils`).

### Added — tests + CI

- **Cross-tenant negative tests** (`tests/test_multi_tenant_isolation.py`
  — 6 cases) covering read / list / write / delete returning **404**
  (not 403) for cross-tenant access, plus SSE topic refusal (403)
  and own-tenant SSE allowed (positive control).
- **Webhook delivery + dead-letter** (`tests/test_webhook_delivery.py`)
  — pending → done on 2xx with `X-Orbiteus-Signature` HMAC, pending →
  retries → `dead` on 5xx with bounded `MAX_RETRIES`.
- **Rate-limit buckets** (`tests/test_rate_limit_buckets.py`) — IP,
  user, tenant; assertions on the canonical 429 body shape and
  `Retry-After` header.
- **Aggregate endpoint** (`tests/test_aggregate_endpoint.py`) — 8
  cases: count/sum, Decimal→float coercion, op/measure/model/field
  validation, tenant isolation.
- **FK resolution** (`tests/test_fk_resolution.py`) — `?expand=...`
  resolves names, NULL FKs stay NULL, unknown columns silently
  ignored, no-leak without expand.
- **Audit semantics** (`tests/test_audit_actor_semantics.py`) — login
  success/fail rows + password reset rows + actor allow-list.
- **AI streaming** (`tests/test_ai_streaming.py`) — default fallback,
  native streaming pass-through, dispatch on `?stream=1`.
- **Vitest per-widget tests** (`admin-ui/src/{lib,components/widgets}/
  *.test.{ts,tsx}`) — 5 files / 32 cases covering `viewParser`,
  `formatters`, `realtime` topic conversion + EventSource shape,
  `StatusBadge` colour map, `MonetaryField` Intl formatting.
- **Playwright E2E** — 5 deterministic scenarios in
  `admin-ui/e2e/critical-path.spec.ts` plus 6 env-gated scenarios
  (cross-tab realtime, audit-log realtime, Cmd-K palette, create
  person, kanban, webhook-test) for seeded tenants.
- **CI gate** (`.github/workflows/ci.yml`) — six parallel jobs (docs,
  backend pytest+cov, frontend vitest+build, Playwright, security
  audits, license check) plus a `gate` aggregator for branch
  protection.
- **Coverage report** (pytest-cov) configured in
  `backend/pyproject.toml`. Canonical run hits **80 % TOTAL** across
  `orbiteus_core` + `modules`; `coverage.xml` artifact published from
  CI.

### Changed

- `docs/34-inventory-and-status.md` rewritten — replaced the
  aspirational "100% across every layer" table with a per-section
  DoD ledger (16 sections, 83 / 90 in-scope checkboxes). The seven
  remaining items are categorised explicitly (3 deliberate post-v1.0
  punts, 2 release-branch follow-ups, 1 paper cut, 1 hardening pass).

### Deferred to post-v1.0

The following items are explicitly outside the v1.0.0 GA scope and
documented in `docs/pre-prompt.md` "Consciously Deferred Framework
Primitives":

- Generic workflow engine (Temporal explicitly excluded — ADR-0015).
- Per-module backend coverage thresholds (`orbiteus_core ≥ 90%`,
  etc.) — host-side `pytest --cov` under-reports the integration
  paths that run inside the backend container; raising those
  thresholds requires an in-container coverage collector.
- `<AIDashboard>` React component (backend `/api/ai/dashboard`
  scaffolded — UI placeholder until the dashboard wave).
- AI move-the-lead E2E test (Playwright seeded variant).

## [1.0.0] — 2026-05-03 (engine snapshot, archival)

First **Engine v1.0** — boring tech stack, AI-native, ready for adopters.

### Added

- **Documentation foundation** — 36 numbered chapters in `docs/`, 16 ADRs,
  `pre-prompt.md` for AI agents, validator (`scripts/check_docs.py`).
- **Production HTTP server** — Gunicorn + UvicornWorker with tunable
  workers / timeout / max-requests (ADR-0011).
- **Connection pooling** — PgBouncer in transaction mode in front of
  Postgres 16 (ADR-0012).
- **One-shot migrate service** in `docker-compose.prod.yml`; backend
  depends on its successful completion. Alembic upgrades wrapped in
  `pg_advisory_lock` for multi-replica safety.
- **Observability** — JSON logging with `request_id`/`tenant_id`/`actor`
  context vars, `/metrics` Prometheus endpoint, `/api/health/live` and
  `/api/health/ready`.
- **Repository hooks + audit log (mandatory, opt-out)** — every CRUD writes
  `base_audit_log` with `actor=user|ai|system`, redacted diff (ADR-0010).
- **EventBus + Postgres Outbox** — durable side-effect queue committed
  atomically with the business transaction (ADR-0010).
- **Celery 5 + Beat** — outbox drainer, HMAC webhook delivery,
  release-stuck-processing schedule (ADR-0013, ADR-0015).
- **Redis cache + rate limit + JWT `jti` revocation** — tighter auth
  defaults (15 min access / 7 day refresh + rotation flag).
- **Realtime SSE** — `/api/realtime/subscribe` with Redis Pub/Sub
  cross-replica fan-out and topic RBAC (ADR-0006, ADR-0014).
- **AI layer (BYOK)** — Fernet-encrypted `base_ai_credential`, Anthropic /
  OpenAI / Ollama provider adapters, `AIModuleConfig` registry per module,
  `pgvector` embeddings with HNSW index, `/api/ai/credentials`,
  `/api/ai/chat`, `/api/ai/dashboard`, monthly token budget guard, PII
  redaction (ADR-0004, ADR-0005, ADR-0009).
- **Canonical CRM** — Person / Lead / Stage / Team replaces
  Customer / Opportunity / Pipeline. `crm/bootstrap.py` seeds default
  stages + Sales team. Demo `ai.py` declares accessible models, callable
  actions, embeddings, suggested prompts (ADR-0008).
- **Admin UI cleanup** — npm workspaces with `packages/ui` shared widgets
  (Badge / Monetary / Statusbar / Many2OneSelect / TagsField) and AI
  components (`<PromptInput>`, `<AIChatPanel>`, `<AIDashboard>`). All
  hardcoded module pages removed; only catch-all routes remain (ADR-0016).
- **Portal UI** — separate Next.js app at `portal-ui/` with share-link
  exchange (`/s/[token]`) backed by `POST /api/auth/share` and
  `GET /api/portal/exchange` (ADR-0007).
- **Backups** — `scripts/backup_db.sh` (pg_dump + gzip + retention) and
  `scripts/restore_drill.sh` (schema-diff drill).

### Changed

- **No Temporal in MVP** (ADR-0015). `worker.py` and
  `orbiteus_core/temporal.py` removed; replaced by Celery + Outbox.
- **Mantine 9 is the only design system** for both apps (ADR-0002 — locks
  the choice of Mantine, not a specific major).
- Default Postgres image is **`pgvector/pgvector:pg16`** in dev and prod
  compose.

### Removed

- Hardcoded admin-ui pages under `app/{crm,base,technical}/*`.
- `Sidebar.tsx` (replaced by `AppShellLayout` dynamic sidebar).
- Temporal Python SDK dependency.

### Migrations

Three new Alembic revisions ship with this release:

1. `a1f3c0e1b002_audit_log_and_attribution` — `base_audit_log` +
   `created_by_id`/`modified_by_id` on every business table.
2. `b2a4e1c0d003_outbox_and_webhooks` — `base_outbox` + `base_webhooks`.
3. `c3b5d2e1c004_ai_credentials_and_embeddings` — pgvector extension,
   `base_ai_credentials`, `base_embeddings` with HNSW index.
4. `d4c0a1f2e005_canonical_crm` — drops legacy
   `crm_customers`/`crm_opportunities`/`crm_pipelines`, recreates
   `crm_stages`, creates `crm_persons`/`crm_teams`/`crm_leads`.

Adopters running v0.x must back up first and run `alembic upgrade head`
inside the new `migrate` compose service.

### Security

- JWT `jti` revocation list on logout / refresh rotation.
- Provider keys encrypted at rest with Fernet (`AI_SECRET_KEY` from env).
- All migrations guarded by `pg_advisory_lock(11534116837)`.
- Production refuses to start with default `SECRET_KEY` /
  `BOOTSTRAP_ADMIN_PASSWORD` (existing safeguard, retained).

### Tests + CI

- 152/152 top-level tests green.
- `scripts/check_docs.py` link & structure validator.
- GitHub Actions workflows: `docs.yml` (docs validator), `secrets.yml`
  (`detect-secrets` baseline scan).
- Playwright config + 5 critical-path E2E scenarios in `admin-ui/e2e/`
  (login, dashboard, create person, kanban, health probe).
- `pre-commit-config.yaml` ships `detect-secrets`, `end-of-file-fixer`,
  `trailing-whitespace`, `check-merge-conflict`, `check-yaml`,
  `check-added-large-files`.

### Final 100% items (DoD §3, §12, §13, §15, §16)

- TOTP **recovery codes** — `orbiteus_core.security.recovery_codes`,
  endpoint `POST /api/auth/2fa/recovery-codes`, login flow consumes a
  matched code (single-use, bcrypt-hashed at rest).
- Portal **mutations** — `POST /api/portal/comment` and
  `POST /api/portal/attachment` enforce share-link permissions and audit
  with `actor=portal`.
- **OpenTelemetry** auto-wire — `orbiteus_core.observability.tracing.setup_tracing`
  attaches OTLP HTTP exporter and instruments FastAPI / SQLAlchemy /
  redis / httpx when `OTEL_EXPORTER_OTLP_ENDPOINT` is set.
- **Playwright** E2E scaffolding (config + spec + npm script).
- **detect-secrets** pre-commit + GitHub Action; `.secrets.baseline`
  ships with sane plugin set.
