import type { MessageCatalog } from "./core";

/** Minimal catalog for unit tests (production catalogs live in modules/base/i18n). */
export const TEST_MESSAGE_CATALOGS: Record<string, MessageCatalog> = {
  en: {
    "common.save": "Save",
    "common.cancel": "Cancel",
    "form.editTitle": "Edit — {title}",
  },
  pl: {
    "common.save": "Zapisz",
    "form.editTitle": "Edycja — {title}",
  },
};
