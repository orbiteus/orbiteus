# Module spec template

Copy to `modules/<name>/docs/spec.md` before implementation.
See `docs/39-spec-driven-agent-workflow.md`.

## 1. Purpose

Who uses this module? What business process does it replace or support?

## 2. Personas and roles

| Persona | Goals | RBAC sketch |
|---|---|---|
| | | |

## 3. Process flow

1. Step one …
2. Step two …

## 4. Models

| Model | Purpose | Key fields |
|---|---|---|
| `<module>.<entity>` | | |

## 5. Views

| Model | Tier A (auto-CRUD) | Tier B (custom UI) |
|---|---|---|
| | list/form/kanban | |

## 6. Integrations

- Events emitted / consumed
- External APIs

## 7. Out of scope

- …

## 8. Acceptance checks

- [ ] List → create → edit → delete
- [ ] RBAC enforced
- [ ] Tests + docs in same PR
