# ADR-0020: TanStack Query for admin-ui data layer

- **Status:** Accepted
- **Date:** 2026-05-29
- **Context tags:** frontend, admin-ui, performance, ai-agents

## Context

The generic admin UI loads every list and form via `useEffect` + local
`loading` state. Navigation shows full-page spinners even when data was
fetched seconds earlier. Reference domain apps (e.g. CalTraining) use
TanStack Query for cache, deduplication, prefetch, and
`placeholderData` (stale-while-revalidate UX).

AI agents building on Orbiteus benefit from predictable query keys and
fewer redundant HTTP round-trips when iterating on modules.

## Decision

Add **`@tanstack/react-query`** (v5) to the authoritative frontend stack
for **`admin-ui`** and **`portal-ui`**.

Defaults (both apps):

- `staleTime: 60_000` ms for ui-config, lists, and record detail
- `refetchOnWindowFocus: false` globally; opt-in per critical view
- `placeholderData: (prev) => prev` on paginated lists and record edit
- Query keys live in each app's `src/lib/queryKeys.ts`

The dynamic catch-all routes (`[module]/[model]`) remain; Query replaces
hand-rolled fetch state only.

## Consequences

- `docs/pre-prompt.md` §3 lists TanStack Query as an allowed dependency.
- `invalidateUiConfigCache()` must call `queryClient.invalidateQueries`.
- New list/form features use hooks in `lib/queries/` — not raw
  `useEffect` fetches.
- **portal-ui:** share-link view + portal mutations use `lib/queries/share.ts`.

## Alternatives considered

- **SWR** — rejected: TanStack Query is already proven in our reference
  product; mutation + invalidation API is clearer for CRUD.
- **Keep module-level Promise cache** — rejected: no prefetch, no
  shared cache between components, no stale-while-revalidate.
- **Redux Toolkit Query** — rejected: heavier; not in boring-tech list.

## References

- `docs/08-admin-ui.md` — data layer section
- `docs/24-tree-spec-admin-ui.md` — §13
- `docs/40-reference-product-caltrain.md` — reference UX patterns
