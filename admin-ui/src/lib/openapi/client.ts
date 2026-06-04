/**
 * Typed OpenAPI surface for admin-ui code.
 *
 * Regenerate when the API changes:
 *   npm run codegen --workspace admin-ui
 *
 * Prefer runtime helpers in `@/lib/api` (`fetchList`, `fetchOne`, mutations).
 * Use these types for request/response shapes only.
 */
import type { components, paths } from "./schema";

export type ApiPaths = paths;
export type ApiSchemas = components["schemas"];

/** Generic list envelope returned by auto-CRUD list endpoints. */
export type ApiListEnvelope<T> = {
  items: T[];
  total: number;
  limit?: number;
  offset?: number;
};

/** Base agent resource (generated from OpenAPI). */
export type AgentRead = ApiSchemas["AgentRead"];
