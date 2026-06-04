export type ComponentStatus = "ok" | "degraded" | "skipped" | "unknown";

export type SystemComponent = {
  id: string;
  name: string;
  group: string;
  status: ComponentStatus;
  message: string;
  latency_ms: number | null;
  detail: Record<string, unknown>;
};

export type SystemStatusPayload = {
  status: ComponentStatus;
  checked_at: string;
  components: SystemComponent[];
};

/** Mantine badge / theme icon color — semantic, not primary chrome. */
export function statusColor(status: ComponentStatus): string {
  switch (status) {
    case "ok":
      return "green";
    case "degraded":
      return "red";
    case "skipped":
      return "gray";
    case "unknown":
      return "yellow";
    default:
      return "gray";
  }
}

export function statusLabel(status: ComponentStatus): string {
  switch (status) {
    case "ok":
      return "Healthy";
    case "degraded":
      return "Degraded";
    case "skipped":
      return "Not used";
    case "unknown":
      return "Unknown";
    default:
      return status;
  }
}

/** Groups aligned with docs/pre-prompt.md §3 stack sections. */
export const GROUP_LABELS: Record<string, string> = {
  runtime: "Runtime",
  persistence: "Persistence & ORM",
  data: "Data services",
  engine: "Engine (orbiteus_core)",
  ai: "AI layer",
  async: "Async & queues",
  infra: "Infrastructure",
  frontend: "Frontends",
};

export const GROUP_ORDER = [
  "runtime",
  "persistence",
  "data",
  "engine",
  "ai",
  "async",
  "infra",
  "frontend",
] as const;

/** Colorful tile accents per component id (data/semantics, not UI chrome). */
export const COMPONENT_TILE_COLORS: Record<string, string> = {
  python: "dark",
  fastapi: "teal",
  http_server: "cyan",
  sqlalchemy: "indigo",
  asyncpg: "blue",
  alembic: "violet",
  postgresql: "blue",
  pgvector: "grape",
  pgbouncer: "cyan",
  pydantic: "pink",
  redis: "red",
  cache: "orange",
  module_registry: "dark",
  rbac: "yellow",
  audit: "gray",
  event_bus: "lime",
  realtime: "teal",
  auth_jwt: "grape",
  ai_module_config: "pink",
  ai_action_palette: "grape",
  ai_agents: "violet",
  ai_credentials: "cyan",
  ai_secret_key: "yellow",
  ai_embeddings: "teal",
  ai_agent_runs: "indigo",
  ai_providers: "blue",
  ai_tooling: "pink",
  prometheus: "orange",
  celery_lib: "violet",
  celery_worker: "grape",
  celery_beat: "violet",
  outbox: "orange",
  nginx: "green",
  docker: "blue",
  nextjs: "dark",
  react: "cyan",
  mantine: "violet",
  admin_ui: "dark",
  portal_ui: "cyan",
};

export function componentTileColor(id: string): string {
  return COMPONENT_TILE_COLORS[id] ?? "gray";
}

export function groupComponents(components: SystemComponent[]): Map<string, SystemComponent[]> {
  const map = new Map<string, SystemComponent[]>();
  for (const comp of components) {
    const list = map.get(comp.group) ?? [];
    list.push(comp);
    map.set(comp.group, list);
  }
  return map;
}

export function semverLabel(raw: string): string {
  return raw.replace(/^\^/, "").replace(/^~/, "");
}
