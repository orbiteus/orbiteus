# 26 — Canonical CRM (Person / Lead / Stage / Team)

> Last reviewed: 2026-05-29.

This chapter documents the **canonical CRM data shape** adopted in
[ADR-0008](./adr/0008-crm-mvp-rename-person-lead-stage-team.md). It is the
reference domain model for demos, agent recipes, and future `crm` (or
domain-specific) modules — not a guarantee that a CRM module is installed in
every distribution.

## Model map (MVP)

| Legacy (pre-ADR-0008) | Canonical | Notes |
|---|---|---|
| `crm.customer` | `crm.person` | `kind ∈ {lead, customer, contact}` |
| `crm.opportunity` | `crm.lead` | Pipeline entity for sales motion |
| `crm.pipeline` | *(removed in MVP)* | Re-introduce when multi-pipeline is required |
| `crm.stage` | `crm.stage` | Ordered stages per team |
| — | `crm.team` | Leader + members |

## UI and modules

- Admin routes for CRM are **auto-rendered** from view specs and RBAC — no
  hard-coded CRM pages (see [ADR-0022](./adr/0022-modern-views-and-rbac-v2.md)).
- The optional reference `crm` module may be absent in minimal installs
  (v1.1.0+); migrations and ADRs still describe the canonical names so new
  domain apps stay aligned.

## Related docs

- [03 — Modules](./03-modules.md) — module layout and manifests
- [ADR-0021](./adr/0021-domain-apps-and-repositioning.md) — domain-first apps
- [40 — Reference product](./40-reference-product-caltrain.md) — example domain app
