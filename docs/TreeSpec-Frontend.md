# Orbiteus — Phase 3: Frontend Specification & Dependency Tree

> Living document. Check boxes [x] as items are completed.
> Last updated: 2026-03-19

---

## 1. Vision

The frontend is a **zero-TSX-per-module dynamic renderer**. A developer writes Python
(manifest + model + schemas + actions) and the frontend auto-renders list views, form views,
kanban boards, and command palette actions — without touching any TypeScript file.

The frontend reads `GET /api/base/ui-config` at startup and builds the entire UI from that
contract. XML view definitions (list/form/kanban) override auto-generated defaults when present.

**Definition of Done for Phase 3:**
> `registry.register("hr")` → restart backend → open browser → sidebar shows HR,
> list view renders columns from Pydantic, form has correct field types,
> Cmd+K shows HR actions — all without a single TSX edit.

---

## 2. Current State (as-is)

### What works
- `AppShellLayout` — responsive sidebar, header, Cmd+K button, token-gated
- `CommandPalette` — Cmd+K modal, debounced search, grouped results, keyboard nav
- `ResourceList` — generic table: search, sort, paginate, delete
- `ResourceForm` — generic form: text, email, tel, number, textarea, select, boolean, date
- `ResourceKanban` — drag-drop kanban board (dnd-kit), optimistic updates
- `ViewSwitcher` — toggles list/kanban via URL param (?view=kanban)
- Dynamic catch-all routes: `/[module]/[model]/*` auto-renders from ui-config
- `lib/api.ts` — axios with Bearer token, 401 redirect
- `lib/modelConfig.ts` — ui-config cache, modelToColumns(), modelToFields()
- `lib/viewParser.ts` — XML arch parser for list/form views
- `lib/branding.tsx` — context provider for white-label (name, logo, favicon)
- Login page with JWT flow
- 33 files total in src/

### What's broken or incomplete
- **Hardcoded pages** — CRM customers, opportunities, pipelines, base/*, technical/* have
  hardcoded page.tsx files that duplicate what dynamic routes already do
- **Polish remnants** — some hardcoded pages still have Polish labels
- **Technical create forms** — pages have createHref but no form page
- **Dashboard** — just says "Welcome to Orbiteus", no widgets or stats
- **Many2one widget** — forms show raw UUID for FK fields instead of related record name
- **Badge widget** — status fields render as plain text, no colored badges
- **Monetary widget** — amounts render as raw numbers, no currency formatting
- **Date display** — dates render as ISO strings in lists, no locale formatting
- **Readonly fields** — parsed from XML but not enforced in form
- **View types** — only list + kanban work; calendar, graph, pivot, activities are stubs
- **No frontend tests** — zero test files

---

## 3. Specification

### 3.1 Layout & Navigation

The `AppShellLayout` renders a left sidebar populated from ui-config modules, a top header
with app name (from branding), Cmd+K search button, and user menu. The sidebar groups models
under module headings (CRM, Base, Technical, etc.). Hidden modules: `auth`. The sidebar
collapses on mobile (burger toggle). The header shows the branding logo if configured.

### 3.2 Dynamic Page Rendering

All module/model pages are rendered by three catch-all routes:
- `/[module]/[model]/page.tsx` — list or kanban view
- `/[module]/[model]/new/page.tsx` — create form
- `/[module]/[model]/[id]/page.tsx` — edit form

Each page fetches ui-config, finds the matching model, and renders using `ResourceList`,
`ResourceForm`, or `ResourceKanban`. No per-module TSX exists — everything is generated.

The XML `<list>` arch controls column order and visibility. The XML `<form>` arch controls
field order, grouping, and widget hints. If no XML view exists, fields are auto-generated
from Pydantic schema metadata.

### 3.3 Widget System

Fields in forms and lists render through a widget system. The widget type is determined by:
1. Explicit `widget="badge"` attribute in XML view arch
2. Field type from Pydantic schema (`str` → text, `bool` → switch, `int` → number)
3. Field name heuristics (`email` → email input, `phone` → tel input)

Required widgets:
- **text** — standard TextInput
- **email** — TextInput type="email"
- **tel** — TextInput type="tel"
- **number** — NumberInput
- **textarea** — Textarea (multi-line)
- **boolean** — Switch toggle
- **date** — DateInput (Mantine date picker)
- **select** — Select dropdown with static options
- **many2one** — Select dropdown that fetches options from related model API endpoint.
  Display format: record's `name` field. Store: UUID.
- **badge** — Colored badge in list view. Colors mapped by value (e.g. active=green,
  draft=gray, won=green, lost=red). In form view renders as select with colored indicator.
- **monetary** — NumberInput with currency suffix from model or company settings.
  List view formats with locale (e.g. "12 500,00 PLN").
- **statusbar** — Horizontal step indicator in form header showing progression
  (e.g. Draft → Confirmed → Done). Clickable to change status.
- **tags** — Multi-value chip display (JSON array field). Editable via TagsInput.
- **readonly** — Any widget can be readonly (grayed out, no interaction).

### 3.4 View Types

Each model can declare available view types. The ViewSwitcher shows tabs for available views.

- **list** — Table with sortable columns, search, pagination, bulk actions. Default view.
- **form** — Record detail/edit form with field groups and widgets.
- **kanban** — Drag-drop board. Requires `default_group_by` in kanban arch.
- **calendar** — Monthly/weekly calendar. Requires `date_start` field in arch. Uses dayjs.
- **graph** — Bar/line/pie chart. Requires `measure` and `groupby` in arch.
- **pivot** — Pivot table / cross-tab aggregation. Defer to Phase 4.
- **activities** — Timeline of actions/notes on a record. Defer to Phase 4.

### 3.5 Command Palette

Cmd+K opens a search modal. Queries `GET /api/ai/actions?q=&limit=12`. Results grouped by
category (create → navigate → search → report → execute). Keyboard navigable. Enter executes
action (usually router.push to target_url). Labels and descriptions in English, keywords
multilingual for fuzzy matching.

### 3.6 Toast Notifications

After every CRUD operation, a toast notification appears:
- Create success: "Record created" (green)
- Update success: "Record updated" (green)
- Delete success: "Record deleted" (orange)
- Error: "Failed to save: {message}" (red)

Uses Mantine `notifications.show()`.

### 3.7 Error Handling

- API errors: parse Pydantic validation errors, show per-field error messages in form.
- Network errors: global toast "Connection error".
- 401: automatic logout + redirect to /login.
- 403: toast "Access denied".
- 404: toast "Record not found".

### 3.8 Branding & White-label

App name, logo URL, and favicon URL loaded from `GET /api/base/branding` (backed by
ir_config_param table). Overridable via env vars. The sidebar header shows logo or app name.
Login page shows logo. Browser tab shows favicon + app name.

### 3.9 Responsive Layout

- Desktop (>1024px): sidebar always visible, full table
- Tablet (768-1024px): sidebar collapsible via burger, table scrolls horizontally
- Mobile (<768px): sidebar hidden by default, burger toggle, stacked form fields

### 3.10 Cleanup

All hardcoded per-module pages (CRM, base, technical) must be removed once the dynamic
routes can fully replace them. The dynamic routes + ui-config + XML views must handle
everything these hardcoded pages currently do.

---

## 4. Dependency Tree

> Legend:
> - `[x]` = done
> - `[ ]` = not done
> - Indented items depend on their parent being done first
> - Items at same level can be done in parallel

```
PHASE 3 — FRONTEND
│
├── 3.0 INFRASTRUCTURE
│   ├── [x] 3.0.1 Next.js 14 App Router + Mantine 8 dark theme
│   ├── [x] 3.0.2 Axios API layer with Bearer token + 401 redirect (lib/api.ts)
│   ├── [x] 3.0.3 UI config fetcher + cache (lib/modelConfig.ts)
│   ├── [x] 3.0.4 XML view arch parser (lib/viewParser.ts)
│   ├── [x] 3.0.5 Branding context provider (lib/branding.tsx)
│   ├── [x] 3.0.6 next.config.mjs /api/* proxy to backend
│   └── [ ] 3.0.7 Translate all remaining Polish strings to English
│
├── 3.1 LAYOUT & NAVIGATION
│   ├── [x] 3.1.1 AppShellLayout — sidebar + header + content area
│   ├── [x] 3.1.2 Dynamic sidebar from ui-config (modules → models)
│   ├── [x] 3.1.3 Header: app name (branding), Cmd+K button, user menu
│   ├── [x] 3.1.4 Login page + JWT token storage + redirect
│   ├── [ ] 3.1.5 Responsive sidebar collapse (burger toggle on mobile/tablet)
│   ├── [ ] 3.1.6 User menu: profile link, language switcher, logout
│   ├── [ ] 3.1.7 Breadcrumbs: Module > Model > Record name
│   └── [ ] 3.1.8 Dashboard home page with stats widgets
│       └── depends on: 3.5.5 (graph widget) or hardcoded stats API
│
├── 3.2 WIDGET SYSTEM
│   ├── [x] 3.2.1 text — TextInput
│   ├── [x] 3.2.2 email — TextInput type="email"
│   ├── [x] 3.2.3 tel — TextInput type="tel"
│   ├── [x] 3.2.4 number — NumberInput
│   ├── [x] 3.2.5 textarea — Textarea
│   ├── [x] 3.2.6 boolean — Switch toggle
│   ├── [x] 3.2.7 date — DateInput (basic)
│   ├── [x] 3.2.8 select — Select dropdown (static options)
│   ├── [ ] 3.2.9 select — Dynamic options from optionsResource (API fetch)
│   │   └── depends on: 3.2.8
│   ├── [ ] 3.2.10 many2one — Select that fetches related model records
│   │   ├── depends on: 3.2.9
│   │   └── Display: record.name | Store: UUID
│   │   └── Search: debounced text input → GET /api/{related}?name__contains=X
│   ├── [ ] 3.2.11 badge — Colored badge for status fields in list view
│   │   └── Color map: { active: "green", draft: "gray", prospect: "blue",
│   │       customer: "green", lead: "yellow", churned: "red",
│   │       won: "green", lost: "red" }
│   ├── [ ] 3.2.12 monetary — NumberInput with currency suffix + locale format in list
│   │   └── Currency from model field or company.currency_code
│   ├── [ ] 3.2.13 statusbar — Horizontal step indicator in form header
│   │   ├── depends on: 3.2.8 (uses select options to know steps)
│   │   └── Clickable steps to change status value
│   ├── [ ] 3.2.14 tags — TagsInput for JSON array fields
│   ├── [ ] 3.2.15 readonly — Any widget grayed out + disabled when readonly=true
│   │   └── depends on: viewParser already parses readonly attr
│   ├── [ ] 3.2.16 date display — Format dates as locale string in list columns
│   │   └── Use dayjs (already in deps) for formatting
│   └── [ ] 3.2.17 Widget registry — map widget name → React component
│       └── depends on: all widgets above
│       └── viewParser returns widget hint → registry resolves to component
│
├── 3.3 LIST VIEW
│   ├── [x] 3.3.1 ResourceList — table with columns from ui-config
│   ├── [x] 3.3.2 Server-side search via ?name__contains= query param
│   ├── [x] 3.3.3 Column sorting (click header → order_by + order_dir)
│   ├── [x] 3.3.4 Pagination (offset/limit, page numbers)
│   ├── [x] 3.3.5 Delete per row (confirm modal → DELETE)
│   ├── [x] 3.3.6 "New" button → /[module]/[model]/new
│   ├── [ ] 3.3.7 Column widget rendering (badge, monetary, date format, many2one name)
│   │   └── depends on: 3.2.11, 3.2.12, 3.2.16, 3.2.10
│   ├── [ ] 3.3.8 Bulk actions: select multiple → delete / export CSV
│   ├── [ ] 3.3.9 Quick filters: status badges above table (click to filter)
│   └── [ ] 3.3.10 Empty state: illustration + "No records yet" + "Create first" button
│
├── 3.4 FORM VIEW
│   ├── [x] 3.4.1 ResourceForm — fields from ui-config or XML arch
│   ├── [x] 3.4.2 Create mode (POST) and edit mode (GET + PUT)
│   ├── [x] 3.4.3 Client-side required validation
│   ├── [x] 3.4.4 Server-side Pydantic error parsing (per-field)
│   ├── [x] 3.4.5 Delete button in edit mode
│   ├── [ ] 3.4.6 Form field groups (sections with headers from XML <group>)
│   │   └── depends on: viewParser update to parse <group string="...">
│   ├── [ ] 3.4.7 Many2one fields render as searchable select
│   │   └── depends on: 3.2.10
│   ├── [ ] 3.4.8 Statusbar widget at top of form
│   │   └── depends on: 3.2.13
│   ├── [ ] 3.4.9 Readonly fields (disabled inputs)
│   │   └── depends on: 3.2.15
│   ├── [ ] 3.4.10 Chatter / activity log sidebar (Phase 4 — defer)
│   └── [ ] 3.4.11 Form tabs (e.g. "Details" | "Notes" | "History")
│       └── depends on: viewParser update to parse <notebook><page string="...">
│
├── 3.5 ADDITIONAL VIEW TYPES
│   ├── [x] 3.5.1 Kanban board — drag-drop, group by field, optimistic update
│   ├── [x] 3.5.2 ViewSwitcher — toggle list/kanban via ?view= param
│   ├── [ ] 3.5.3 Kanban card enhancement — show badge, monetary, avatar
│   │   └── depends on: 3.2.11, 3.2.12
│   ├── [ ] 3.5.4 Calendar view — monthly/weekly, events from date fields
│   │   └── requires: arch attribute date_start, optional date_end
│   │   └── library: @mantine/dates (already in stack) or custom with dayjs
│   ├── [ ] 3.5.5 Graph view — bar/line/pie from aggregated data
│   │   └── requires: arch attributes measure, groupby
│   │   └── library: recharts or @mantine/charts
│   ├── [ ] 3.5.6 Pivot table — defer to Phase 4
│   └── [ ] 3.5.7 Activities timeline — defer to Phase 4
│
├── 3.6 COMMAND PALETTE
│   ├── [x] 3.6.1 Cmd+K global modal
│   ├── [x] 3.6.2 Debounced search → GET /api/ai/actions
│   ├── [x] 3.6.3 Results grouped by category
│   ├── [x] 3.6.4 Keyboard navigation (↑↓ Enter Esc)
│   ├── [x] 3.6.5 English labels, multilingual keywords
│   ├── [ ] 3.6.6 Recent actions section (localStorage last 5 used)
│   └── [ ] 3.6.7 "?" prefix → Smart Search (LLM filter generation) — Phase 4
│
├── 3.7 NOTIFICATIONS & ERRORS
│   ├── [ ] 3.7.1 Toast on create/update/delete success
│   │   └── Use Mantine notifications.show()
│   ├── [ ] 3.7.2 Toast on API error (red, with message)
│   ├── [ ] 3.7.3 403 handling — "Access denied" toast
│   ├── [ ] 3.7.4 404 handling — "Record not found" toast
│   ├── [ ] 3.7.5 Network error handling — "Connection lost" toast
│   └── [ ] 3.7.6 Form-level error banner (aggregated validation errors)
│
├── 3.8 CLEANUP & POLISH
│   ├── [ ] 3.8.1 Remove all hardcoded CRM pages (customers/, opportunities/, pipelines/)
│   │   └── depends on: 3.2.10, 3.2.11, 3.2.12 (dynamic routes must handle what hardcoded did)
│   ├── [ ] 3.8.2 Remove all hardcoded base pages (companies/, partners/, users/)
│   │   └── depends on: 3.8.1
│   ├── [ ] 3.8.3 Remove all hardcoded technical pages
│   │   └── depends on: 3.8.1
│   ├── [ ] 3.8.4 Remove legacy Sidebar.tsx (deprecated)
│   ├── [ ] 3.8.5 Translate all remaining Polish strings to English
│   ├── [ ] 3.8.6 Empty state for lists and forms (no data illustration)
│   └── [ ] 3.8.7 Loading skeletons for list/form/kanban
│
├── 3.9 RESPONSIVE DESIGN
│   ├── [ ] 3.9.1 Sidebar: collapsible on tablet, hidden on mobile + burger toggle
│   ├── [ ] 3.9.2 Table: horizontal scroll on small screens
│   ├── [ ] 3.9.3 Form: single column on mobile, two columns on desktop
│   └── [ ] 3.9.4 Kanban: horizontal scroll on mobile, fewer visible columns
│
└── 3.10 TESTING
    ├── [ ] 3.10.1 Vitest + React Testing Library setup
    ├── [ ] 3.10.2 Unit tests: viewParser (XML → columns/fields)
    ├── [ ] 3.10.3 Unit tests: modelConfig (ui-config → columns/fields)
    ├── [ ] 3.10.4 Component tests: ResourceList renders columns from config
    ├── [ ] 3.10.5 Component tests: ResourceForm renders fields from config
    ├── [ ] 3.10.6 Component tests: CommandPalette search + navigation
    └── [ ] 3.10.7 E2E smoke test: login → list → create → edit → delete
```

---

## 5. Implementation Priority (what to do first)

### Wave 1 — Core widgets (unblock hardcoded page removal)
```
3.2.10 many2one widget
3.2.11 badge widget
3.2.12 monetary widget
3.2.16 date display formatting
3.7.1  toast notifications (success)
3.7.2  toast notifications (error)
```

### Wave 2 — Form improvements
```
3.2.13 statusbar widget
3.2.15 readonly fields
3.4.6  form groups (sections)
3.4.11 form tabs (notebook)
3.2.17 widget registry
```

### Wave 3 — Cleanup
```
3.8.1  remove hardcoded CRM pages
3.8.2  remove hardcoded base pages
3.8.3  remove hardcoded technical pages
3.8.4  remove legacy Sidebar.tsx
3.8.5  translate remaining Polish
3.0.7  final i18n pass
```

### Wave 4 — Additional views
```
3.5.4  calendar view
3.5.5  graph view
3.5.3  kanban card enhancements
```

### Wave 5 — Polish & responsive
```
3.9.1  responsive sidebar
3.9.2  responsive table
3.1.7  breadcrumbs
3.1.8  dashboard home page
3.3.10 empty state
3.8.7  loading skeletons
```

### Wave 6 — Testing
```
3.10.1-7  all test items
```

### Deferred to Phase 4
```
3.5.6  pivot table
3.5.7  activities timeline
3.4.10 chatter sidebar
3.6.7  Smart Search (? prefix LLM)
3.3.8  bulk actions
```

---

## 6. File Impact Map

| Item | Files created/modified |
|------|----------------------|
| 3.2.10 many2one | `components/widgets/Many2One.tsx` (new), `ResourceForm.tsx` |
| 3.2.11 badge | `components/widgets/Badge.tsx` (new), `ResourceList.tsx` |
| 3.2.12 monetary | `components/widgets/Monetary.tsx` (new), `ResourceList.tsx`, `ResourceForm.tsx` |
| 3.2.13 statusbar | `components/widgets/Statusbar.tsx` (new), `ResourceForm.tsx` |
| 3.2.17 registry | `components/widgets/index.ts` (new) |
| 3.4.6 groups | `lib/viewParser.ts`, `ResourceForm.tsx` |
| 3.4.11 tabs | `lib/viewParser.ts`, `ResourceForm.tsx` |
| 3.5.4 calendar | `components/ResourceCalendar.tsx` (new), `[module]/[model]/page.tsx` |
| 3.5.5 graph | `components/ResourceGraph.tsx` (new), `[module]/[model]/page.tsx` |
| 3.7.* toasts | `ResourceForm.tsx`, `ResourceList.tsx`, `ResourceKanban.tsx` |
| 3.8.1-3 cleanup | Delete 15+ hardcoded page files |
| 3.9.* responsive | `AppShellLayout.tsx`, `ResourceList.tsx`, `ResourceForm.tsx` |
