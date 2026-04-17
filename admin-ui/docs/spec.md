# Admin UI — Specification

> Status: IMPLEMENTED (v0.1)
> Stack: Next.js 14 (App Router) + Mantine 8 + axios

---

## Cel

Generyczny admin panel dla engine. White-label — nazwa i logo z API.
Każdy nowy moduł backendowy automatycznie dostaje ekrany w UI przez auto-CRUD.

---

## Architektura

```
/admin-ui/src/
├── app/                          # Next.js App Router pages
│   ├── layout.tsx                # Root: MantineProvider + BrandingProvider
│   ├── page.tsx                  # Dashboard
│   ├── login/page.tsx            # Strona logowania
│   ├── crm/
│   │   ├── customers/page.tsx
│   │   ├── opportunities/page.tsx
│   │   └── pipelines/page.tsx
│   ├── base/
│   │   ├── companies/page.tsx
│   │   ├── users/page.tsx
│   │   └── partners/page.tsx
│   └── technical/
│       ├── models/page.tsx
│       ├── access/page.tsx
│       ├── rules/page.tsx
│       ├── params/page.tsx
│       ├── sequences/page.tsx
│       └── crons/page.tsx
├── components/
│   ├── AppShellLayout.tsx        # Sidebar + Header (Mantine AppShell)
│   ├── ResourceList.tsx          # Generic list view
│   ├── ResourceForm.tsx          # TODO: Generic create/edit form
│   └── ResourceKanban.tsx        # TODO: Generic kanban view
└── lib/
    ├── api.ts                    # axios instance + interceptors
    └── branding.tsx              # BrandingContext + useBranding()
```

---

## Komponenty generyczne

### ResourceList (DONE)
```tsx
<ResourceList
  title="Klienci"
  resource="crm/customer"
  createHref="/crm/customers/new"
  columns={[
    { key: "name", label: "Nazwa" },
    { key: "status", label: "Status", render: (v) => <Badge>{v}</Badge> },
  ]}
/>
```
- Fetches GET /api/{resource}
- Mantine Table (striped, dark theme)
- Loading state, error state, empty state
- "Nowy" button → createHref

### ResourceForm (TODO — Faza 1)
```tsx
<ResourceForm
  title="Nowy klient"
  resource="crm/customer"
  fields={[
    { key: "name", label: "Nazwa", type: "text", required: true },
    { key: "email", label: "Email", type: "email" },
    { key: "status", label: "Status", type: "select",
      options: ["lead", "prospect", "customer"] },
  ]}
  onSuccess={(record) => router.push(`/crm/customers/${record.id}`)}
/>
```
- POST/PUT /api/{resource} lub /api/{resource}/{id}
- Mantine TextInput, Select, Textarea, DateInput itp.
- Inline validation (z Pydantic error messages)
- Loading state na submit

### ResourceKanban (TODO — Faza 1)
```tsx
<ResourceKanban
  resource="crm/opportunity"
  groupBy="stage_id"
  groupsResource="crm/stage"
  card={(record) => <OpportunityCard record={record} />}
  onMove={(recordId, newGroupId) => api.post(...)}
/>
```
- Drag & drop między kolumnami (biblioteka: @dnd-kit)
- Optimistic update przy drag
- Fetch groups (stages) + records per group

---

## Routing convention

```
/crm/customers          → list
/crm/customers/new      → create form
/crm/customers/{id}     → view/edit form
/crm/opportunities      → list
/crm/opportunities/kanban → kanban view
```

---

## Auth flow

1. Brak tokena w localStorage → redirect /login
2. Formularz login → POST /api/auth/login
3. Token zapisany w localStorage
4. axios interceptor request → dodaje Authorization: Bearer {token}
5. axios interceptor response 401 → clear token + redirect /login
6. Wylogowanie → clear localStorage + redirect /login

---

## Branding

```
GET /api/base/branding → {name, logo_url, favicon_url}
  ↓
BrandingContext (React Context)
  ↓
useBranding() hook
  ↓
AppShellLayout (header: logo lub nazwa)
LoginPage (title: logo lub nazwa)
layout.tsx (metadata title)

Fallback: NEXT_PUBLIC_APP_NAME z .env.local
```

---

## Design system

- **Framework:** Mantine 8
- **Motyw:** dark (czarne tło dark-9, sidebar dark-8)
- **Primary color:** dark (monochrome)
- **Ikony:** @tabler/icons-react
- **Font:** Inter

### Kolory (Mantine dark palette)
```
dark-9: #101113  ← main background
dark-8: #141517  ← sidebar, header
dark-7: #1A1B1E  ← table background
dark-6: #25262b  ← borders
dark-5: #2C2E33  ← input borders
gray-2: #C1C2C5  ← primary text
gray-4: #909296  ← secondary text / dimmed
```

---

## TODO

| Feature | Priority |
|---|---|
| ResourceForm (Create/Edit) | High |
| Delete z potwierdzeniem (Modal) | High |
| ResourceKanban + drag&drop | High |
| Breadcrumbs | Medium |
| Pagination w ResourceList | Medium |
| Search/filter w ResourceList | Medium |
| ResourceCalendar | Medium |
| Notifications (toast) przy akcjach | Medium |
| Dark/Light mode toggle | Low |
