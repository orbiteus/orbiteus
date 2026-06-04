import type { MessageCatalog } from "./core";

/**
 * UI message catalogs are owned by modules (canonical: modules/base/i18n/en.json).
 * The SPA loads merged catalogs from GET /api/base/i18n/messages/{lang}.
 * This export is an empty fallback for SSR/tests only.
 */
export const MESSAGE_CATALOGS: Record<string, MessageCatalog> = {
  en: {},
};

export { NAV_LABEL_KEYS, translateNavLabel } from "./nav";
