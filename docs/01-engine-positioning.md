# 01 — Engine Positioning

## What Orbiteus is

Orbiteus is an **engine** for **AI agents** building **domain business
applications** — CRM, club ops, HR, integrations, and operational tools
that fill gaps left by generic SaaS. It sits between a pure framework and
a finished ERP product:

| Category | Example | Provides |
|---|---|---|
| Framework (pure) | Flask, Express | Abstractions only — devs build everything |
| Batteries-included framework | Django, Rails | + ORM, auth, admin scaffolding |
| **Engine** | **Orbiteus** | + UI shell, RBAC, multitenancy, AI/realtime/audit, **generic admin CRUD**, **CRM showcase domain module** |
| Domain product | CalTraining (reference), HubSpot | Ready app for one industry/process |
| Full ERP | Odoo, SAP | Accounting, localization, statutory modules |

Orbiteus **does not** ship statutory accounting or country-specific tax
engines. Ambitious adopters may extend the architecture toward ERP-scale
modules; the engine must not block that (see ADR-0021).

**Reference product:** CalTraining (LadiesGym) — fitness CRM replacing
Pipedrive; documented in `docs/40-reference-product-caltrain.md`.

Orbiteus ships:

- A **framework layer** (`orbiteus_core`, `modules/base`, `modules/auth`).
- An **AI layer** (providers, BYOK, tools, embeddings, prompts, dashboards).
- A **showcase domain module** (`modules/crm` — Person / Lead / Stage / Team; the
  reference app agents copy when adding new modules).
- Two front-ends (`admin-ui` for internal users, `portal-ui` for external partners)
  built on Mantine 9 plus in-app widgets under `admin-ui/src/orbiteus-ui/`.

The promise: an AI agent (or senior engineer) cloning the repo and running
`docker compose up` gets production-grade skeleton (auth, RBAC, audit, AI,
realtime) and a working CRM showcase in minutes — then implements **domain
logic from spec** (`docs/39-spec-driven-agent-workflow.md`) in days, not
months of plumbing.

## Where the boundary runs

| Layer | Belongs in framework | Does not belong |
|---|---|---|
| `orbiteus_core` | Module Registry, BaseRepository, AutoRouter, ui-config, JWT, RBAC, audit, EventBus, Outbox, Cache, Realtime, AI provider abstraction, sequences, attachments, mail engine, report engine | A specific Customer / Invoice / Department model |
| `modules/base` | `users`, `roles`, `companies`, `tenants`, all `base_*` system tables (model_access, rule, sequence, attachment, message, activity, cron, audit_log, embedding, ai_credential, outbox) | Sales pipelines, employees, projects |
| `modules/auth` | JWT login/refresh/2FA, password reset, share-link tokens (portal scope) | Onboarding to a specific product |
| `modules/crm` *(showcase domain module)* | Person, Lead, Stage, Team, kanban/calendar/graph views, `actions.py`, `ai.py` | Industry-specific extensions in client forks |
| `modules/hr`, `project`, `social` *(samples)* | Optional reference modules — can be deleted in client deployments | Same as above |
| `admin-ui` | AppShell, dynamic renderer, widget registry, branding, ⌘K, AI chat panel, TanStack Query data layer (ADR-0020) | Optional Tier B feature routes for CRM-heavy UX (ADR-0021) |
| `portal-ui` | Public layout, share-link entry, RBAC-scoped resource views (read + comments) | Internal CRM / HR navigation |

## Showcase domain module policy

`modules/crm` **ships with the engine** as the **sole in-repo showcase domain
app** (a module is a domain app). It has three jobs:

1. Prove that a single module can deliver List, Kanban, Calendar, and Graph views
   without per-model TSX (Tier A).
2. Show how `ai.py` plugs an AI assistant into a domain.
3. Exercise the framework's audit, realtime, and queue paths end-to-end.

Agents copy CRM layout (`models/`, `views/`, `access/`, `docs/spec.md`) for
new modules. CRM is **not** the framework — client deployments can disable it
(`modules/crm` removed from `registry.register(...)`) without affecting the engine.

## Versioning impact

- A breaking change in **framework layer** requires a major version bump and an ADR.
- A breaking change in **canonical example** requires a minor bump and a migration note.
- Sample modules (`hr`, `project`, `social`) can change at any time — no SLA.

See `21-release-and-versioning.md`.

## When to create a new module vs extend an existing one

Create a new module when:

- The domain is independent (its own RBAC matrix, its own data model).
- It would otherwise force cross-module imports.
- Its data should be optional in some deployments.

Extend an existing module when:

- You add fields, actions, or views to existing models.
- The change does not introduce a new aggregate root.

If unsure, propose a module first and ask the user.
