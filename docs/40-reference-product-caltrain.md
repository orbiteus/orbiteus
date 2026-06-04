# 40 — Reference product: CalTraining (LadiesGym)

> **Reference product** — a domain app built to replace Pipedrive and
> connect call-center scheduling with in-club trainer sales. It
> demonstrates what adopters build **on** Orbiteus-class primitives; it
> is not shipped inside the engine repository today.

## Business problem

LadiesGym needed a **fitness-specific CRM**:

- Call center books trial sessions (calendar-heavy workflow).
- Trainers must **close package sales** during/after trials.
- Pipedrive did not match club operations 1:1.
- Future modules: club operations, HR, BI — **not** statutory accounting.

CalTraining is the model for “domain app in weeks, not months.”

## Architecture pattern (conceptual mapping)

| CalTraining (reference) | Orbiteus engine equivalent |
|---|---|
| FastAPI + Postgres + Redis | Same stack in `backend/` |
| Vite SPA + React Router | Tier B in adopters' own repos; CRM showcase uses admin-ui |
| TanStack Query | ADR-0020 in `admin-ui` |
| OpenAPI codegen | `admin-ui` `npm run codegen` |
| SSE + leader-tab lock | `admin-ui/src/lib/realtimeHub.ts` |
| RBAC + tenant isolation | `BaseRepository`, YAML access |
| Module-specific processes | `modules/<name>/docs/spec.md` |

## What agents should copy

1. **Spec-first** — process documented before models (`docs/39`).
2. **Query cache** — lists and forms feel instant after first load.
3. **Dedicated screens** for the core workflow (calendar, dashboards).
4. **Generic CRUD** for admin tables (users, settings) where possible.
5. **Integration modules** (e.g. Pipedrive outbound) as isolated services.

## What agents should not copy blindly

- JWT in `localStorage` — Orbiteus admin uses httpOnly cookies (ADR-0017).
- shadcn/Tailwind — Mantine 9 only (ADR-0002).
- Replacing Orbiteus module registry with ad-hoc routes.

## Relationship to canonical CRM

`modules/crm` in Orbiteus is the **sole in-repo showcase domain module**
(Person/Lead/Stage/Team + kanban/calendar/graph). Agents should treat it as
the living template for module structure, views, and conventions.

CalTraining is a **production domain app** in a separate repository with
different models and UX. Use CRM to learn engine conventions; use this doc
to learn product depth for fitness/club operations.

## Future modules (planned on reference product)

- Club operations (capacity, equipment, schedules)
- HR (staff, contracts — no payroll localization in engine)
- BI / reporting dashboards

Engine maintainers document patterns here; implementation lives in the
reference product repository. New engine modules follow `modules/crm/` layout.

## References

- ADR-0021
- `docs/39-spec-driven-agent-workflow.md`
- `docs/08-admin-ui.md`
