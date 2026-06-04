import axios from "axios";
import { notifications } from "@mantine/notifications";

// ---------------------------------------------------------------------------
// Types (kept above runtime code — Turbopack in monorepo Docker can fail to
// parse `export interface` when it appears after executable statements).
// ---------------------------------------------------------------------------

export interface FieldMeta {
  name: string;
  type:
    | "text"
    | "email"
    | "tel"
    | "number"
    | "textarea"
    | "select"
    | "boolean"
    | "date"
    | "many2one"
    | "monetary"
    | "tags"
    | "multi_select"
    | "many2many";
  required: boolean;
  label: string;
  /** Target model for many2one, e.g. crm.customer */
  relation?: string;
  options?: { value: string; label: string }[];
  /** Load select options from a list API, e.g. base/role */
  optionsResource?: string;
  optionValue?: string;
  optionLabel?: string;
  /** ISO-4217 code for monetary fields (e.g. "PLN", "EUR"). */
  currency_code?: string;
}

export interface ModelConfig {
  name: string;
  label: string;
  /** Omitted from app catalog; still available via Technical / Settings links. */
  ui_hidden?: boolean;
  fields: FieldMeta[];
  views: {
    list: string | JsonListView | null;
    form: string | JsonFormView | null;
    kanban: string | JsonKanbanView | null;
    search: string | null;
    calendar: string | null;
    graph: string | null;
  };
}

/** JSON view payloads from ui-config (ADR-0022). */
export type JsonListView = {
  model: string;
  type: "list";
  columns: { key: string; label?: string; widget?: string }[];
};

export type JsonFormView = {
  model: string;
  type: "form";
  sections?: { title?: string; fields: string[] }[];
  tabs?: { title: string; sections: { title?: string; fields: string[] }[] }[];
};

export type JsonKanbanView = {
  model: string;
  type: "kanban";
  group_by: string;
  card_fields?: string[];
};

export interface ModuleConfig {
  name: string;
  label: string;
  category: string;
  models: ModelConfig[];
}

export interface UiConfig {
  modules: ModuleConfig[];
}

/**
 * Shared axios instance.
 *
 * - `withCredentials: true` so the browser sends the `orbiteus_token` cookie
 *   on same-origin `/api/*` calls (proxied server-side to FastAPI in
 *   `app/api/[[...path]]/route.ts` so `Set-Cookie` from login is preserved).
 * - No request interceptor injects an Authorization header any more — the
 *   backend reads JWT from the httpOnly cookie set by /api/auth/login.
 *   See docs/adr/0017-httponly-cookie-session.md.
 */
export const api = axios.create({
  baseURL: "/api",
  withCredentials: true,
  /** Avoid an indefinite spinner when the rewrite target or DB is unreachable. */
  timeout: 45_000,
});

// Legacy localStorage cleanup: remove any token left over from the previous
// (pre-cookie) auth model so a returning user doesn't carry stale state.
if (typeof window !== "undefined") {
  try {
    window.localStorage.removeItem("token");
  } catch {
    /* ignore */
  }
}

function toastDetail(err: { response?: { data?: { detail?: unknown } } }): string {
  const d = err.response?.data?.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d) && d[0]?.msg) return String(d[0].msg);
  return "Request failed";
}

/** Must stay aligned with `src/proxy.ts` — pages where 401 is expected (stale cookie + /auth/me). */
function isPublicAuthSurface(pathname: string): boolean {
  if (pathname === "/login" || pathname === "/welcome" || pathname === "/forgot-password") {
    return true;
  }
  return pathname.startsWith("/reset/");
}

api.interceptors.response.use(
  (res) => res,
  (err) => {
    const status = err.response?.status;
    const skip = Boolean(err.config?.skipGlobalErrorToast);

    if (status === 401 && typeof window !== "undefined") {
      // A present-but-expired `orbiteus_token` still passes the Edge proxy
      // (cookie existence only). `/auth/me` then returns 401; redirecting
      // from `/login` would reload forever — only bounce off protected UI.
      const path = window.location.pathname;
      if (!isPublicAuthSurface(path)) {
        const next = `${path}${window.location.search}`;
        const loginUrl = next && next !== "/login"
          ? `/login?next=${encodeURIComponent(next)}`
          : "/login";
        window.location.href = loginUrl;
      }
      return Promise.reject(err);
    }

    if (!skip && typeof window !== "undefined") {
      if (!err.response) {
        notifications.show({
          title: "Network error",
          message: "Connection lost. Check your network and try again.",
          color: "red",
        });
      } else if (status === 403) {
        notifications.show({
          title: "Access denied",
          message: toastDetail(err),
          color: "red",
        });
      } else if (status === 404) {
        notifications.show({
          title: "Not found",
          message: toastDetail(err),
          color: "orange",
        });
      }
    }

    return Promise.reject(err);
  }
);

/** Must stay aligned with `auto_router.py` list `Query(..., le=200)`. */
export const LIST_PAGE_MAX = 200;

export interface ListResponse<T = unknown> {
  items: T[];
  total?: number;
  offset?: number;
  limit?: number;
}

export async function fetchList<T = unknown>(
  resource: string,
  params?: Record<string, unknown>,
): Promise<ListResponse<T>> {
  const { data } = await api.get<ListResponse<T>>(`/${resource}`, { params });
  return data;
}

/** Walks paginated list endpoints until all rows are loaded (cap 10k rows). */
export async function fetchAllListItems<T = unknown>(
  resource: string,
  params?: Record<string, unknown>,
  maxRows = 10_000,
): Promise<T[]> {
  const items: T[] = [];
  let offset = 0;

  while (items.length < maxRows) {
    const limit = Math.min(LIST_PAGE_MAX, maxRows - items.length);
    const page = await fetchList<T>(resource, { ...params, offset, limit });
    const batch = page.items ?? [];
    items.push(...batch);

    const total = page.total ?? items.length;
    offset += batch.length;
    if (batch.length === 0 || offset >= total) break;
  }

  return items;
}

export const USER_FACING_API_ERROR_DEFAULT = "Request failed";

const MAX_USER_DETAIL_LEN = 220;

/** True when API detail text is safe to show in UI (no HTML/proxy noise). */
export function isUserFacingApiDetailSafe(text: string): boolean {
  const t = text.trim();
  if (!t || t.length > MAX_USER_DETAIL_LEN) return false;
  const lower = t.toLowerCase();
  if (lower.includes("<!doctype") || lower.includes("<html") || lower.includes("</")) return false;
  if (lower.includes("traceback") || lower.includes("internal server")) return false;
  if (lower.includes("nginx") || lower.includes("bad gateway")) return false;
  if (lower === "network error" || lower.includes("failed to fetch")) return false;
  if (/^api\s+\d{3}\s*$/i.test(t)) return false;
  return true;
}

function detailFromAxios(err: import("axios").AxiosError): string | null {
  const d = err.response?.data as { detail?: unknown } | undefined;
  const detail = d?.detail;
  if (typeof detail === "string" && detail.trim()) return detail.trim();
  if (Array.isArray(detail) && detail[0]?.msg) return String(detail[0].msg);
  return null;
}

/** User-safe message for toasts and form banners (CalTrain-style filtering). */
export function extractApiError(err: unknown, fallback = USER_FACING_API_ERROR_DEFAULT): string {
  const fb = fallback.trim() || USER_FACING_API_ERROR_DEFAULT;
  if (!axios.isAxiosError(err)) {
    if (err instanceof Error && isUserFacingApiDetailSafe(err.message)) return err.message.trim();
    return fb;
  }
  const raw = detailFromAxios(err);
  if (raw && isUserFacingApiDetailSafe(raw)) return raw;
  if (err.message === "Network Error") return fb;
  return fb;
}

export function apiErrorMessage(err: unknown, fallback = "Request failed"): string {
  return extractApiError(err, fallback);
}

export async function fetchOne<T = Record<string, unknown>>(
  resource: string,
  id: string,
  params?: Record<string, unknown>,
): Promise<T> {
  const { data } = await api.get<T>(`/${resource}/${id}`, {
    params,
    skipGlobalErrorToast: true,
  });
  return data;
}

export async function createRecord(resource: string, payload: unknown) {
  const { data } = await api.post(`/${resource}`, payload, { skipGlobalErrorToast: true });
  return data;
}

export async function updateRecord(resource: string, id: string, payload: unknown) {
  const { data } = await api.put(`/${resource}/${id}`, payload, { skipGlobalErrorToast: true });
  return data;
}

export async function deleteRecord(resource: string, id: string) {
  await api.delete(`/${resource}/${id}`, { skipGlobalErrorToast: true });
}

export async function fetchUiConfig(): Promise<UiConfig> {
  const { data } = await api.get("/base/ui-config");
  return data;
}

export type UiLocaleMeta = {
  code: string;
  label: string;
  dayjs: string;
  source: "core" | "module";
  module: string;
};

export async function fetchUiLocales(): Promise<UiLocaleMeta[]> {
  const { data } = await api.get<{ locales: UiLocaleMeta[] }>("/base/i18n/locales");
  return data.locales;
}

export async function fetchUiMessages(lang: string): Promise<Record<string, string>> {
  const { data } = await api.get<{ lang: string; messages: Record<string, string> }>(
    `/base/i18n/messages/${encodeURIComponent(lang)}`,
  );
  return data.messages;
}
