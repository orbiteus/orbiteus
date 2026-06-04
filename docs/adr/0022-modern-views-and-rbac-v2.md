# ADR-0022: Modern views (JSON) and RBAC v2

- **Status:** Accepted
- **Date:** 2026-05-29
- **Supersedes:** partial replacement of XML-first view loading

## Context

Orbiteus inherited Odoo-shaped primitives (XML views with XPath, `role_ids`
JSON, Python tuple domains for record rules, dual RBAC sources). Runtime
already prefers Pydantic-driven `ui-config`, but XML and string references
created dual sources of truth and fragile front-end parsing (regex on XML).

## Decision

### Views — JSON View Schema (primary)

1. Modules declare views as `views/<model>.<type>.view.json` listed in
   `manifest.data[]`.
2. `orbiteus_core/json_views.py` validates and caches definitions.
3. `GET /api/base/ui-config` embeds parsed JSON in `models[].views.<type>`.
4. XML via `view_loader.py` remains **deprecated fallback** only; new
   modules must not add XML views.

### RBAC — single YAML source

1. Module security lives in `security/access.yaml` only.
2. Python `security.setup()` merge paths are **removed** (CRM included).
3. UI edits to `base.model-access` / `base.record-rule` remain runtime
   overrides; export/sync is a future wave.

### Roles — relational assignment

1. New table `base_user_roles(user_id, role_id)` with FKs.
2. `base_users.role_ids` JSON retained for migration compatibility but
   **written via junction sync**; API exposes role **codes** derived from join.
3. JWT includes `rbac_ver` (integer from Redis `rbac:version`). Middleware
   reloads role codes from DB when token `rbac_ver` < current version.

### Record rules — structured JSON

1. YAML `domain` accepts JSON list of filters:
   `[{"field": "assigned_user_id", "op": "=", "value": "current_user"}]`
2. Legacy Python tuple strings still parse via `ast.literal_eval` on import.
3. DB column `domain_force` stores JSON array (not Python source string).

### Production UX — hide engine tables

Models listed in manifest `ui_hidden_models` are included in `ui-config` with
`ui_hidden: true` for Technical / Settings CRUD routes. Internal-only models
(e.g. `base.registry-model-field`) stay out of `ui-config`.

### Deferred (explicit)

- Field-level RBAC — not v1.0; marked deferred in `docs/05-rbac-multitenancy.md`.
- Casbin / RLS — out of scope; record rules + tenant filter remain.

## Consequences

- Admin UI uses Zod-validated JSON view parser (`viewJson.ts`).
- New dependency: `zod` in admin-ui (view validation only).
- Migration required for `base_user_roles` and domain JSON normalization.
- Tests updated for junction roles and JSON views.

## References

- `docs/05-rbac-multitenancy.md`
- `docs/08-admin-ui.md`
- ADR-0003 (RBAC Redis cache)
