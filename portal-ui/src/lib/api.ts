export interface ShareResourceView {
  resource_model: string;
  resource_id: string;
  permissions: string[];
  tenant_id: string;
  view_mode: "readonly" | "editable";
  available_mutations: string[];
  payload: Record<string, unknown>;
}

export const USER_FACING_API_ERROR_DEFAULT = "Request failed";

export function isUserFacingApiDetailSafe(text: string): boolean {
  const t = text.trim();
  if (!t || t.length > 220) return false;
  const lower = t.toLowerCase();
  if (lower.includes("<!doctype") || lower.includes("<html")) return false;
  if (lower.includes("nginx") || lower.includes("bad gateway")) return false;
  return true;
}

export function extractApiError(err: unknown, fallback = USER_FACING_API_ERROR_DEFAULT): string {
  if (err instanceof Error && err.message && isUserFacingApiDetailSafe(err.message)) {
    return err.message;
  }
  const detail = (err as { detail?: unknown })?.detail;
  if (typeof detail === "string" && isUserFacingApiDetailSafe(detail)) return detail;
  return fallback;
}

async function readJson<T>(res: Response): Promise<T> {
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail =
      typeof (body as { detail?: unknown }).detail === "string"
        ? (body as { detail: string }).detail
        : "Request failed";
    throw new Error(detail);
  }
  return body as T;
}

export async function fetchShareView(token: string): Promise<ShareResourceView> {
  const res = await fetch(`/api/portal/exchange?token=${encodeURIComponent(token)}`);
  return readJson<ShareResourceView>(res);
}

export async function postPortalComment(token: string, body: string): Promise<void> {
  const res = await fetch("/api/portal/comment", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token, body }),
  });
  await readJson(res);
}

export type UiLocaleMeta = {
  code: string;
  label: string;
  dayjs: string;
  source: "core" | "module";
  module: string;
};

export async function fetchUiLocales(): Promise<UiLocaleMeta[]> {
  const res = await fetch("/api/base/i18n/locales");
  const data = await readJson<{ locales: UiLocaleMeta[] }>(res);
  return data.locales;
}

export async function fetchUiMessages(lang: string): Promise<Record<string, string>> {
  const res = await fetch(`/api/base/i18n/messages/${encodeURIComponent(lang)}`);
  const data = await readJson<{ lang: string; messages: Record<string, string> }>(res);
  return data.messages;
}

export async function postPortalAttachment(token: string, file: File): Promise<void> {
  const fd = new FormData();
  fd.append("token", token);
  fd.append("file", file);
  const res = await fetch("/api/portal/attachment", { method: "POST", body: fd });
  await readJson(res);
}
