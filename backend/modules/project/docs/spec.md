# Moduł project — Specification

> Status: TODO (Faza 3)
> depends_on: [base]

---

## Cel modułu

Zarządzanie projektami i zadaniami. Używany przez praktycznie każdy biznes.
Podstawa dla: timesheetów, serwisu, helpdesk.

---

## Modele domenowe

### Project
```python
id, tenant_id, company_id,
name, description,
manager_id,          # FK → base_users
partner_id,          # FK → base_partners (klient)
date_start, date_end,
status,              # "draft" | "active" | "paused" | "done" | "cancelled"
privacy,             # "public" | "private" | "team"
color,               # kolor w UI
tags: list[str],
billable,
allow_timesheets
```
Tabela: `project_projects`

### TaskStage
Etapy zadań. Każdy projekt może mieć własne etapy LUB dzielić globalne.
```python
id, tenant_id,
name, sequence,
project_id,    # NULL = globalny dla wszystkich projektów
is_closed,     # etap zamknięty
fold_in_kanban
```
Tabela: `project_task_stages`

### Task
```python
id, tenant_id, company_id,
name, description,
project_id,
stage_id,
assigned_user_ids: list[UUID],   # może być wiele osób
partner_id,           # kontakt klienta (opcjonalny)
deadline,
planned_hours,
effective_hours,      # z timesheets
priority,             # 0 = normal, 1 = urgent
tags: list[str],
parent_id,            # subtask
sequence,             # kolejność w Kanban
active,
date_closed
```
Tabela: `project_tasks`

### Timesheet (jeśli allow_timesheets=True na projekcie)
```python
id, tenant_id,
task_id, project_id,
user_id,
date,
hours,
description
```
Tabela: `project_timesheets`

---

## Widoki UI

| Widok | Model | Status |
|---|---|---|
| List | Project | TODO |
| List | Task | TODO |
| Kanban | Task (per stage) | TODO |
| Calendar | Task (per deadline) | TODO |
| Form | Project | TODO |
| Form | Task | TODO |
| Gantt | Task timeline | TODO (V2) |

---

## API Custom endpoints
```
GET /api/project/project/{id}/kanban   → tasks grouped by stage
GET /api/project/my-tasks              → zadania przypisane do current_user
POST /api/project/task/{id}/move       → zmiana etapu (drag&drop)
GET /api/project/stats                 → summary
```
