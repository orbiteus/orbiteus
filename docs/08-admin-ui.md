# 08 — Admin UI

## Stack

- Next.js 16 App Router
- React 19
- Mantine 9 (only design system; no shadcn / MUI / Chakra / Ant)
- `admin-ui/src/orbiteus-ui/` — cross-cutting widgets + AI inputs (copy to portal-ui when needed)
- axios, dayjs, recharts, @dnd-kit, @tabler/icons-react
- **@tanstack/react-query** 5 — server-state cache (ADR-0020)

## Data layer (TanStack Query)

Admin UI uses TanStack Query for all auto-CRUD fetches:

- `QueryProvider` wraps the app in `layout.tsx`
- Query keys in `admin-ui/src/lib/queryKeys.ts`
- Hooks in `admin-ui/src/lib/queries/` (`useUiConfig`, `useResourceList`, `useResource`)
- Defaults: `staleTime: 60s`, `refetchOnWindowFocus: false`, `placeholderData`
  on lists and edit forms (stale-while-revalidate — no empty flash)
- **Prefetch:** hovering a list row prefetches `GET /{resource}/{id}` with
  `expand=` for many2one fields on the form
- **Invalidation:** realtime list hook calls `queryClient.invalidateQueries`;
  module catalog toggles call `applyModuleToggleSideEffects()` in
  `lib/moduleRuntime.ts` (`ui-config`, `i18n`, `resource`, `attachments`)
- OpenAPI types: committed `src/lib/openapi/` snapshot + `npm run codegen`;
  CRM typed helpers in `openapi/resources.ts`; CI drift check in E2E job

Do not add raw `useEffect` + `setLoading` for new CRUD surfaces — extend the
query hooks.

## Hybrid UI (Tier A / Tier B)

| Tier | When | Where |
|---|---|---|
| **A** | Simple models, admin tables | Dynamic `[module]/[model]` routes |
| **B** | CRM dashboards, heavy UX | Module feature routes in `admin-ui` (ADR-0021); adopters may ship separate SPAs in their own repos |

Reference: CalTraining patterns in `docs/40-reference-product-caltrain.md`.

| Path | Public? | Purpose |
|---|---|---|
| `/welcome` | yes | Landing page with hub of resources |
| `/login` | yes | Sign-in form (email/password + optional 2FA) |
| `/` | no | Authenticated dashboard |
| `/[module]/[model]` | no | Auto-rendered list / kanban |
| `/[module]/[model]/new` | no | Auto-rendered create form |
| `/[module]/[model]/[id]` | no | Auto-rendered edit form |
| `/modules` | no | Module catalog — list of modules, enable/disable |
| `/users/roles` | no | RBAC roles overview (from model access + record rules) |
| `/base/user` | no | User accounts — companies (many2many), roles (multi-select from `base.role`) |
| `/crm/team` | no | Sales teams — leader user + member users (many2many to `base.user`) |
| `/base/model-access` | no | Access rights matrix (Settings) |
| `/connectivity/mail` | no | SMTP relay settings + connection / send test |
| `/connectivity/webhooks` | no | Outbound webhook subscribers |
| `/technical/system-status` | no | Full engine stack health plus **release version** (`version` field and Orbiteus runtime tile); runtime, persistence, engine subsystems, **AI layer**, async queue, frontends |
| `/technical/attachments` | no | Tenant attachment catalog — search, upload (pick model + record), download, delete |
| `/technical/audit-log` | no | Paginated audit trail with realtime refresh |
| `/base/agent` | no | AI agent definitions (AI → Agents) |
| `/base/agent-run` | no | Agent execution history (AI → Agent runs) |
| `/technical/agent-console` | no | Run agents async with live SSE status |

## Local dev (Docker)

| Item | Value |
|---|---|
| Admin UI | http://localhost:3000/login |
| API (direct) | http://localhost:8000/api/health/live |
| Bootstrap email | `admin@example.com` |
| Bootstrap password | `admin1234` (from `.env.example`) |

The browser session uses httpOnly cookies set by `POST /api/auth/login`
via the Next.js `/api/*` proxy — always sign in through **port 3000**,
not `:8000`.

**Do not** run `next dev --webpack` inside the monorepo Docker image;
webpack resolves a second React copy and pages crash after login
(`Element type is invalid`). Turbopack is the default dev bundler.

Celery Beat writes its schedule file to `/tmp` in compose so Turbopack
does not restart the frontend on every tick.

## Sidebar sections

The left **AppShell** navbar defaults to the **expanded menu** (240px) with
group labels (**Apps** / **System**) and expandable section trees. Use the
**toggle at the bottom** to collapse to the icon rail (56px). **Hover** a
collapsed icon to see its name in a tooltip. **Click a section icon** (CRM, AI,
Settings…) to **drill down** into that section’s submenu when collapsed.
**Back** (←) returns to the top-level section list.
Width preference: `localStorage` (`orbiteus:sidebar-open`; default expanded when
unset). When collapsed,
navigating to a route auto-opens the drill view for the active section unless
you explicitly pressed Back on that page.

Each sidebar group is **expandable** when the rail is expanded (Mantine
`NavLink` with nested children). On first visit every section opens except
**Technical** (engine tables stay collapsed). Open/closed state is stored in
`localStorage` (`orbiteus.sidebar.expanded.v3`); defaults are persisted on
first seed via `initializeExpandedSectionsIfAbsent()` so re-renders after i18n
or ui-config load do not re-trigger default expansion. The section containing the
current route is always forced open on navigation.

Two non-clickable group labels organize the tree:

| Group | Sections |
|---|---|
| *(top)* | **Dashboard** — always visible, not collapsible |
| **Apps** | One expandable block per installed product module (e.g. **CRM**) |
| **System** | **AI**, **Settings**, **Technical** |

| Section | Purpose |
|---|---|
| **CRM** *(example app)* | Person, Lead, Stage, Team — from module manifest |
| **AI** | AI Integration, Agents, Agent runs |
| **Settings** | Users, Roles, Access rights, Mail, Webhooks, Module catalog |
| **Technical** | System status, engine tables (models, rules, parameters, sequences, cron, audit log) |

Dynamic app modules use their manifest label (e.g. **CRM**). Engine routes
under `/base/*` appear in **Settings** or **Technical** by purpose, not by URL
prefix. **Technical → Models** is populated at startup by syncing the in-code
model registry into `base_models` (`registry.seed_registry_to_db()`).

`/welcome` and `/login` are separate routes. **Never merge them.**

## Dynamic rendering

The admin UI is a renderer. Adding a new module **must not** require new TSX.

1. Frontend fetches `GET /api/base/ui-config` via TanStack Query (cached 60s).
2. The catch-all routes `[module]/[model]/*` look up the model in ui-config.
3. **JSON views** (primary, ADR-0022): `views/<model>.<type>.view.json` in
   manifest `data[]` — validated with Zod in `viewJson.ts`.
4. **XML views** (deprecated fallback): legacy `<list>`, `<form>`, `<kanban>`.
5. If no view arch is registered, fields are auto-generated from Pydantic
   schema metadata.

Models listed in manifest `ui_hidden_models` (e.g. `base.registry-model`,
`base.config-param`) are included in ui-config with `"ui_hidden": true` so
Technical / Settings routes get list and form metadata, but they do not appear
in the main app catalog. Internal-only models such as `base.registry-model-field`
are not registered for auto-CRUD and stay out of ui-config.

If you find yourself creating `admin-ui/src/app/<module>/...`, **stop** and
either:
- Add a JSON view in the module's `views/`, or
- Register a new widget for the missing rendering case.

## Widget registry

Forms and lists render through widgets keyed by `widget` attribute or field type:

| Widget | Field type / attribute |
|---|---|
| `text` | `str` |
| `email` | name === "email" |
| `tel` | name in {"phone", "mobile"} |
| `number` | `int` / `float` |
| `textarea` | `widget="textarea"` |
| `boolean` | `bool` |
| `date` | `datetime` |
| `select` | `widget="select"` (static or `optionsResource`) |
| `many2one` | FK ending with `_id` |
| `badge` | `widget="badge"` (status fields) |
| `monetary` | `widget="monetary"` |
| `last_login` | `widget="last_login"` (user list: timestamp + device icon; read-only, set on auth login) |
| `statusbar` | `widget="statusbar"` (form header) |
| `tags` | `list[str]` (JSON array) |
| `readonly` | any widget with `readonly=true` |

To add a new widget: implement it under `admin-ui/src/orbiteus-ui/widgets/` and wire it in
`<ResourceForm>` / `<ResourceList>` as today.

## View types

| View | Required arch attribute | Status |
|---|---|---|
| list | (none) | implemented — compact row list (~38px rows, actions on hover) |
| form | (none) | implemented |
| kanban | `default_group_by` | implemented |
| calendar | `date_start` (and optional `date_end`) | planned (CRM-MVP) |
| graph | `measure`, `group_by` | planned |
| pivot | — | deferred |
| activities | — | deferred |

## Command Palette (⌘K)

- Modal opened by ⌘K (Mac) / Ctrl+K (Win/Linux).
- Searches Actions through `GET /api/ai/actions?q=...`.
- RapidFuzz scoring (~1 ms), no LLM in the happy path.
- Multilingual keyword matching (EN + PL extensible).

⌘K is **deterministic** action search. It is *not* a chat. The chat lives in
`<AIChatPanel>` — see `15-ai-layer.md`.

## AI integration in admin UI

| Component | Purpose |
|---|---|
| `<PromptInput>` | Embeddable text box on any module page; sends query with module's `accessible_models` context |
| `<AIChatPanel>` | Sidebar / drawer chat with tools available to the user |
| `<AIDashboard>` | Prompt → `aggregate` queries → recharts spec |
| `useAIContext(model, id)` | Hook that scopes context to current view |

The four AI entry points live in `admin-ui/src/orbiteus-ui/ai/` — modules do
not call provider SDKs directly.

## Branding

- `useBranding()` returns `{ name, logo_url, favicon_url }` from `base_config_param`.
- Logo, name, and favicon are tenant-controlled.
- The product name is **never** hardcoded in tracked content (see `AGENTS.md`).

## Forbidden patterns

- Per-module page files in `admin-ui/src/app/<module>/...`.
- Direct calls to provider APIs from the front-end.
- A second design system.
- New UI primitives outside the `orbiteus-ui` widget set without an ADR.
- Inline styles that bypass Mantine theme tokens.
