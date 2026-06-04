# OpenAPI types (admin-ui)

Two ways to regenerate TypeScript types from the API contract:

```bash
# Live API (default http://127.0.0.1:8000/api/openapi.json)
npm run codegen --workspace admin-ui

# Offline from committed snapshot
npm run codegen:file --workspace admin-ui
```

Outputs:

- `openapi.json` — committed API snapshot (drift check input)
- `schema.ts` — generated types (`openapi-typescript`)
- `client.ts` — thin re-exports (`CrmLead`, `CrmPerson`, …)
- `resources.ts` — typed CRM fetch helpers (showcase module)

## Drift check

```bash
./scripts/check_openapi_codegen.sh          # uses openapi.json
./scripts/check_openapi_codegen.sh --live   # fetch fresh OpenAPI, then verify schema.ts
```

CI runs the live variant in the E2E job after `docker compose up`.

When you change backend routes or Pydantic models:

1. Start the stack (`docker compose up -d`).
2. Run `./scripts/check_openapi_codegen.sh --live`.
3. Commit both `openapi.json` and `schema.ts`.

## Usage

Import types from `@/lib/openapi/client`. Typed CRM calls:
`@/lib/openapi/resources.ts`. Runtime + cache: `@/lib/api` and TanStack Query.
