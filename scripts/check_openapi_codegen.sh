#!/usr/bin/env sh
# Regenerate admin-ui OpenAPI types and fail if schema.ts drifts from openapi.json.
#
# Usage:
#   ./scripts/check_openapi_codegen.sh          # file-based (CI / offline)
#   OPENAPI_URL=http://127.0.0.1:8000/api/openapi.json ./scripts/check_openapi_codegen.sh --live
set -eu

ROOT="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
OPENAPI_JSON="$ROOT/admin-ui/src/lib/openapi/openapi.json"
SCHEMA_TS="$ROOT/admin-ui/src/lib/openapi/schema.ts"

cd "$ROOT"

if [ "${1:-}" = "--live" ]; then
  URL="${OPENAPI_URL:-http://127.0.0.1:8000/api/openapi.json}"
  echo "Fetching OpenAPI from $URL"
  curl -fsS "$URL" -o "$OPENAPI_JSON"
fi

if [ ! -f "$OPENAPI_JSON" ]; then
  echo "Missing $OPENAPI_JSON — run export or pass --live with API up." >&2
  exit 1
fi

npm run codegen:file --workspace admin-ui

if git diff --quiet -- "$SCHEMA_TS"; then
  echo "OpenAPI types are up to date."
else
  echo "OpenAPI drift: admin-ui/src/lib/openapi/schema.ts is out of date." >&2
  git diff -- "$SCHEMA_TS" | head -80 >&2 || true
  exit 1
fi
