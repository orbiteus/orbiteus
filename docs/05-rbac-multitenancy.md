# 05 — RBAC & Multi-tenancy

Orbiteus enforces five layers of access control. Every read or write goes
through `BaseRepository`, which applies them automatically.

## Tenant isolation (Layer 0 — always on)

- `tenant_id` is required on every business table.
- `BaseRepository._tenant_filter()` injects `WHERE tenant_id = ctx.tenant_id`
  on every query.
- Bypass requires `RequestContext.is_superadmin = True` and is logged with
  `actor=system` plus the call stack.

## Layer 1 — Model access (`base_model_access`)

```
role × model → {read, write, create, unlink}
```

- Loaded into Redis at `registry.bootstrap()`.
- Cached for ≤ 60 s; invalidated on `base_model_access` change events.
- Checked in `BaseRepository._check_model_access()`.

## Layer 2 — Record rules (`base_rule`)

Structured JSON domain filters that restrict rows for specific roles:

```yaml
domain:
  - field: assigned_user_id
    op: "="
    value: current_user
```

Legacy Odoo-style tuple strings are normalized on YAML import. Stored in
`domain_force` as a JSON array. Applied automatically in
`BaseRepository.search()` and `get()`.

## Layer 3 — User role assignment (`base_user_roles`)

Role codes are assigned via junction table `base_user_roles(user_id, role_id)`.
The API still exposes `role_ids` as a list of role **codes**; JWT carries
`rbac_ver` (Redis `rbac:version`). When RBAC changes, middleware reloads role
codes from the junction without requiring re-login.

## Layer 4 — Action RBAC

Every `Action` declares `requires_feature`. The resolver filters actions out
of the Command Palette and AI tool list when the user lacks the feature.

The mapping:

```
feature "crm.persons.manage" → model "crm.person", op "write"
```

## Layer 5 — Field-level (deferred)

Per-field `read` / `write` per role was considered for v1.0 but is **deferred**.
Do not implement ad-hoc field filtering without a new ADR.

## Layer 6 — Scope (`internal` / `portal` / `ai`)

JWT carries a `scope` claim. The scope is the **upper bound** on what a request
can do, regardless of role:

| Scope | Allowed |
|---|---|
| `internal` | Admin UI, full RBAC matrix |
| `portal` | Only models declared as portal-shareable; default read-only |
| `ai` | Inherits the issuing user's permissions; never grants more |

`portal` tokens are issued from share links (see `06-auth.md`).
`ai` tokens are derived from the human user's context for the duration of an
AI tool call; AI never holds a long-lived token.

## RequestContext

```python
@dataclass
class RequestContext:
    tenant_id: UUID | None
    company_id: UUID | None
    user_id: UUID | None
    roles: list[str]
    scope: str = "internal"     # internal | portal | ai
    is_superadmin: bool = False
    request_id: str | None = None
    actor: str = "user"         # user | ai | system
```

## Superadmin escape hatch

- One bootstrap superadmin per instance (env vars `BOOTSTRAP_ADMIN_*`).
- Bypasses tenant isolation **only when explicitly requested**
  (`ctx.is_superadmin and ctx.tenant_id is None`).
- Every superadmin call is audited with `actor=user` and a `superadmin=true` flag.
- In production, the bootstrap password must be rotated on first login;
  `Settings.validate_production_safety` blocks startup with the default password.

## Common pitfalls (don't)

- Don't pass `RequestContext()` with no `tenant_id` to `BaseRepository` outside
  of system-level code paths.
- Don't cache RBAC decisions for > 60 s; users get added to roles in real time.
- Don't grant the `ai` scope to scheduled jobs — use `actor=system` with an
  explicit RBAC scope.
- Don't share `share_link` tokens beyond the resource they were minted for.
