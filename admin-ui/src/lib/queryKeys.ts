/** TanStack Query keys — keep stable for prefetch + invalidation. */

export const queryKeys = {
  uiConfig: () => ["ui-config"] as const,
  i18nLocales: () => ["i18n", "locales"] as const,
  i18nMessages: (lang: string) => ["i18n", "messages", lang] as const,
  resourceList: (resource: string, params: Record<string, unknown>) =>
    ["resource", "list", resource, params] as const,
  resourceDetail: (resource: string, id: string, expand?: string) =>
    ["resource", "detail", resource, id, expand ?? ""] as const,
  attachments: (params: object = {}) =>
    ["attachments", "list", params] as const,
};
