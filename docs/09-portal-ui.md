# 09 — Portal UI (External Partner Portal)

## Purpose

A separate Next.js 16 application (`portal-ui/`) for **external** users —
clients, partners, contractors. Same engine, same backend, same design system,
different attack surface and different RBAC scope.

Use cases:

- Client sees a project's tasks read-only and can comment.
- Partner sees a shared lead, accepts/rejects.
- External reviewer accesses a single document with limited actions.

## Why a separate app

- **Different threat model** — anonymous and link-bound users vs authenticated employees.
- **Different routes** — no internal navigation, no module sidebar.
- **Different bundles** — smaller, faster, no admin widgets.
- **Different CSP / headers** — strict for portal, more permissive for admin.
- **Different domains** — portal lives on `portal.example.com` (or per-tenant
  subdomain); admin on `app.example.com`.

## Authentication entry points

| Entry | How |
|---|---|
| Share link | `/s/<token>` exchanges a portal-scoped JWT for a session cookie |
| Tenant-branded portal user | Email + password (separate `portal_users` table) |
| Magic link | One-time email link → session |

All three issue tokens with `scope=portal`. The token is never accepted by
admin-ui.

## RBAC scope: `portal`

- The token is bound to a resource (`aud` claim) and a permission set.
- Default: read-only.
- Optional: `comment`, `attach_file`, `update_status` per resource type.
- Each portal action goes through the same `BaseRepository` with a
  `RequestContext(scope="portal", roles=["portal_user"])`.

## Routes

| Path | Purpose |
|---|---|
| `/s/[token]` | Share-link exchange page |
| `/login` | Portal login (when tenant enabled) |
| `/dashboard` | List of resources the user has access to |
| `/r/[type]/[id]` | Resource view (tasks, leads, projects, ...) |

## Module declarations

A module exposes resources to the portal via `view/portal_views.xml`:

```xml
<portal name="project.task">
  <fields read="title,description,due_date,status,comments" />
  <actions>
    <action id="comment" />
    <action id="upload_attachment" />
  </actions>
</portal>
```

The portal-ui renders only declared fields and actions; everything else is
hidden by default.

## Realtime in portal

- Portal users get the same SSE primitives as internal users.
- Topics scoped to their `aud` resources only — no fan-out across tenants
  or unrelated resources.

## Data layer (TanStack Query)

Portal UI uses TanStack Query for share-link data and portal mutations
(ADR-0020):

- `QueryProvider` in `layout.tsx`
- `queryKeys.shareView(token)` for `/api/portal/exchange`
- `useShareResourceView`, `usePortalComment`, `usePortalAttachment` in
  `src/lib/queries/share.ts`
- Realtime events call `refetch()` on the share query (same pattern as admin
  list invalidation)
- `placeholderData` on the share view — no flash on refetch after comment

Do not add raw `useEffect` fetch loops for new portal surfaces.

## What is forbidden in portal

- Browsing models that did not declare a `<portal>` view.
- Mutating any field other than those declared in `<actions>`.
- Generating share links from inside the portal (only internal users do).
- Direct API calls to module endpoints — portal goes through `/api/portal/*`
  which enforces `scope=portal`.

## Status

Portal UI is planned for v0.3. Skeleton tracking lives in
`25-tree-spec-portal-ui.md`. ADR `0007` covers the "separate app" decision.
