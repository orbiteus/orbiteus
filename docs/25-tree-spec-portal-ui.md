# 25 — Tree Spec: Portal UI

> External partner portal. Last reviewed: 2026-05-03.
> All items planned for Wave 5 (see `22-implementation-plan.md`).

## 1. App scaffolding

- [x] 1.1 Create `portal-ui/` Next.js 16 app
- [ ] 1.2 Copy shared widgets from `admin-ui/src/orbiteus-ui` when portal needs them
- [ ] 1.3 Tailored layout: no module sidebar, focused on shared resource
- [ ] 1.4 `next.config.js` `/api/portal/*` proxy
- [ ] 1.5 Strict CSP and `frame-ancestors 'none'` (no embedding)
- [ ] 1.6 Tenant-aware theming via `useBranding()` (same as admin)

## 2. Auth entry points

- [ ] 2.1 `/s/[token]` share-link exchange page
- [ ] 2.2 `/login` portal-user login (when tenant enables)
- [ ] 2.3 Magic-link flow (`POST /api/auth/portal/magic`)
- [ ] 2.4 Cookie session bound to scope=portal
- [ ] 2.5 CSRF (double-submit cookie + `SameSite=Strict`)

## 3. Resource views

- [ ] 3.1 `/dashboard` — list of accessible resources for the user
- [ ] 3.2 `/r/[type]/[id]` — resource detail (read-only by default)
- [ ] 3.3 Comments thread (when `comment` action declared)
- [ ] 3.4 File upload (when `attach_file` action declared)
- [ ] 3.5 Status update (when `update_status` action declared)
- [ ] 3.6 Realtime updates (SSE) for resources the user can see

## 4. Module declarations

- [ ] 4.1 `<portal>` view parser in `view/portal_views.xml`
- [ ] 4.2 Backend filter to expose only declared fields and actions
- [ ] 4.3 Validation: portal cannot mutate fields outside `<actions>`
- [ ] 4.4 Default deny: any model without `<portal>` is invisible

## 5. AI in portal (limited)

- [ ] 5.1 `<PromptInput>` available, scoped to the single shared resource
- [ ] 5.2 Tools restricted to `read` on declared models only
- [ ] 5.3 No write actions exposed to AI in portal scope

## 6. Tests

- [ ] 6.1 E2E: share link → portal opens → resource visible read-only
- [ ] 6.2 E2E: comment → admin sees realtime update
- [ ] 6.3 Negative test: portal cannot access non-declared model (`403`)
- [ ] 6.4 Negative test: portal cannot read other tenants
- [x] 6.5 Vitest: queryKeys + api error helpers
- [x] 6.6 TanStack Query on share view + portal mutations (ADR-0020)
