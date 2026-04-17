# Moduł crm — Specification

> Status: IMPLEMENTED (v0.1) — podstawowy CRUD
> depends_on: [base]

---

## Cel modułu

Zarządzanie relacjami z klientami. Lejek sprzedaży (pipeline), szanse sprzedaży (opportunities),
klienci (customers). Podstawa dla każdego biznesu.

---

## Modele domenowe

### Customer
Klient firmy. Różni się od Partner — jest wzbogacony o dane handlowe.
```python
id, tenant_id, company_id,
name, email, phone, mobile,
status,          # "lead" | "prospect" | "customer" | "churned"
is_company,
city, country_code, street,
vat, website,
assigned_user_id,   # opiekun handlowy
tags: list[str],
source,             # skąd pochodzi: "website" | "referral" | "cold_call"
create_date, write_date
```
Tabela: `crm_customers`

### Pipeline
Lejek sprzedaży. Firma może mieć wiele pipeline'ów (np. B2B, B2C).
```python
id, tenant_id, company_id,
name, currency_code, is_default
```
Tabela: `crm_pipelines`

### Stage
Etap w pipeline. Zamknięte etapy: won, lost.
```python
id, tenant_id, company_id,
pipeline_id, name, sequence,
probability,         # domyślne prawdopodobieństwo wygrania na tym etapie
is_won, is_lost,     # etapy zamknięcia
fold_in_kanban       # zwinięty w widoku Kanban
```
Tabela: `crm_stages`

### Opportunity
Szansa sprzedaży. Serce CRM.
```python
id, tenant_id, company_id,
name,
customer_id,         # FK → crm_customers
pipeline_id,         # FK → crm_pipelines
stage_id,            # FK → crm_stages
assigned_user_id,    # opiekun
expected_revenue,    # wartość szansy
probability,         # % wygrania (0-100)
close_date,          # planowana data zamknięcia
description,
tags: list[str],
lost_reason,         # powód przegranej
won_date,            # data wygrania
create_date, write_date
```
Tabela: `crm_opportunities`

---

## API Endpoints

### Auto-CRUD
```
GET/POST        /api/crm/customer
GET/PUT/DELETE  /api/crm/customer/{id}

GET/POST        /api/crm/pipeline
GET/PUT/DELETE  /api/crm/pipeline/{id}

GET/POST        /api/crm/stage
GET/PUT/DELETE  /api/crm/stage/{id}

GET/POST        /api/crm/opportunity
GET/PUT/DELETE  /api/crm/opportunity/{id}
```

### Custom endpoints
```
GET  /api/crm/pipeline/{id}/kanban
     → {stages: [{stage, opportunities: [...]}]}
     → dla widoku Kanban w UI

POST /api/crm/opportunity/{id}/move
     → {stage_id}
     → przenosi okazję do innego etapu + trigger Temporal signal

GET  /api/crm/stats
     → {total_customers, open_opportunities, total_revenue, win_rate}
```

---

## Widoki UI

| Widok | Model | Status |
|---|---|---|
| List | Customer | DONE |
| List | Opportunity | DONE |
| List | Pipeline | DONE |
| Form | Customer | TODO |
| Form | Opportunity | TODO |
| Kanban | Opportunity (per pipeline) | TODO |
| Dashboard | CRM stats | TODO |

---

## Record Rules (Security)

```python
# Salesman widzi tylko swoje szanse
RecordRule(
    model="crm.opportunity",
    role="crm.salesman",
    domain=[("assigned_user_id", "=", "current_user")]
)
# Manager widzi wszystkie szanse w firmie
# (brak rule = brak filtru = widzi wszystko w swoim company)
```

---

## Roles

| Rola | Uprawnienia |
|---|---|
| crm.salesman | CRUD własne opportunities, read customers |
| crm.manager | CRUD wszystkie opportunities, pipelines, stages |

---

## Workflow (Temporal)

### move_opportunity_to_stage
Trigger przy `POST /api/crm/opportunity/{id}/move`.

Wykonuje:
1. Zmiana stage_id
2. Aktualizacja probability na wartość domyślną nowego etapu
3. Jeśli stage.is_won → set won_date = now()
4. Jeśli stage.is_lost → require lost_reason
5. Signal do Temporal (np. trigger automatycznego emaila)

---

## TODO

| Feature | Priority | Uwagi |
|---|---|---|
| Kanban view w UI | High | Generic ResourceKanban komponent |
| Form Create/Edit | High | Generic ResourceForm komponent |
| Activity log per opportunity | High | Moduł social (Faza 2) |
| Chatter per opportunity | High | Moduł social (Faza 2) |
| Email sending on stage change | Medium | Moduł mail |
| Duplicate detection | Medium | Podobne nazwy customer |
| Lead scoring | Low | ML-based |
| Revenue forecasting | Low | |
