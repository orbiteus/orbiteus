# Moduł hr — Specification

> Status: TODO (Faza 3)
> depends_on: [base]

---

## Cel modułu

Zarządzanie pracownikami. Różnica między User a Employee:
- **User** — konto do logowania w systemie (techniczne)
- **Employee** — osoba zatrudniona (biznesowe: stanowisko, dział, umowa, wynagrodzenie)

Jeden User może być powiązany z jednym Employee. Employee może nie mieć dostępu do systemu.

---

## Modele domenowe

### Department
```python
id, tenant_id, company_id,
name, parent_id,   # hierarchia działów
manager_id         # FK → Employee
```

### JobPosition
```python
id, tenant_id, company_id,
name, department_id,
expected_employees,   # ile osób na tym stanowisku
```

### Employee
```python
id, tenant_id, company_id,
name, job_title, job_position_id,
department_id, manager_id,
user_id,           # FK → base_users (opcjonalne — nie każdy employee ma konto)
work_email, work_phone, mobile_phone,
address_id,        # FK → base_partners
private_email,
gender, birthday, marital_status,
nationality, id_number,
contract_type,     # "full_time" | "part_time" | "b2b" | "contractor"
employment_date, termination_date,
active
```
Tabela: `hr_employees`

### Contract
```python
id, tenant_id, employee_id,
name, contract_type,
date_start, date_end,
wage, currency_code,
notes
```
Tabela: `hr_contracts`

---

## Widoki UI

| Widok | Model | Status |
|---|---|---|
| List | Employee | TODO |
| Form | Employee | TODO |
| Org Chart | Department tree | TODO (V2) |

---

## TODO
- Timesheets (depends on project)
- Leave management
- Payroll (V2)
