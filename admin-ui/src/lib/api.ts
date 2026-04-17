import axios from "axios";
import { notifications } from "@mantine/notifications";

export const api = axios.create({
  baseURL: "/api",
});

api.interceptors.request.use((config) => {
  const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

function toastDetail(err: { response?: { data?: { detail?: unknown } } }): string {
  const d = err.response?.data?.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d) && d[0]?.msg) return String(d[0].msg);
  return "Request failed";
}

api.interceptors.response.use(
  (res) => res,
  (err) => {
    const status = err.response?.status;
    const skip = Boolean(err.config?.skipGlobalErrorToast);

    if (status === 401 && typeof window !== "undefined") {
      localStorage.removeItem("token");
      window.location.href = "/login";
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

export async function fetchList(resource: string, params?: Record<string, unknown>) {
  const { data } = await api.get(`/${resource}`, { params });
  return data; // { items, total, offset, limit }
}

export async function fetchOne(resource: string, id: string) {
  const { data } = await api.get(`/${resource}/${id}`);
  return data;
}

export async function createRecord(resource: string, payload: unknown) {
  const { data } = await api.post(`/${resource}`, payload);
  return data;
}

export async function updateRecord(resource: string, id: string, payload: unknown) {
  const { data } = await api.put(`/${resource}/${id}`, payload);
  return data;
}

export async function deleteRecord(resource: string, id: string) {
  await api.delete(`/${resource}/${id}`);
}

export async function fetchUiConfig(): Promise<UiConfig> {
  const { data } = await api.get("/base/ui-config");
  return data;
}

// ---------------------------------------------------------------------------
// Types
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
    | "tags";
  required: boolean;
  label: string;
  /** Target model for many2one, e.g. crm.customer */
  relation?: string;
  options?: { value: string; label: string }[];
}

export interface ModelConfig {
  name: string;
  label: string;
  fields: FieldMeta[];
  views: {
    list: string | null;
    form: string | null;
    kanban: string | null;
    search: string | null;
    calendar: string | null;
    graph: string | null;
  };
}

export interface ModuleConfig {
  name: string;
  label: string;
  category: string;
  models: ModelConfig[];
}

export interface UiConfig {
  modules: ModuleConfig[];
}
