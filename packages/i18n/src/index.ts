export {
  COMMON_TIMEZONES,
  DAYJS_LOCALE,
  DEFAULT_UI_LANGUAGE,
  LANGUAGE_LABELS,
  SUPPORTED_UI_LANGUAGES,
  createTranslator,
  detectBrowserLanguage,
  isKnownUiLanguage,
  isUiLanguage,
  normalizeUiLanguage,
  type KnownUiLanguage,
  type MessageCatalog,
  type TranslateVars,
  type Translator,
  type UiLanguage,
} from "./core";

export {
  mergeAllCatalogs,
  mergeMessageCatalogs,
  type LanguagePack,
} from "./packs";

export {
  buildRuntimeCatalogs,
  getRegisteredLanguageCodes,
  getRegisteredLocaleMeta,
  registerLanguagePack,
  registerLocaleMeta,
  resolveDayjsLocale,
  type LocaleMeta,
} from "./registry";

export {
  MESSAGE_CATALOGS,
  NAV_LABEL_KEYS,
  translateNavLabel,
} from "./messages";

export {
  fieldLabelKey,
  modelLabelKey,
  sectionLabelKey,
  slugifySection,
  translateFieldLabel,
  translateModelLabel,
  translateSectionLabel,
  viewLabelKey,
} from "./meta";

export { I18nProvider, useI18n, useT, type I18nContextValue } from "./react";

export { PUBLIC_PAGE_FALLBACK_EN } from "./public-page-fallbacks";
export { SHELL_FALLBACK_EN } from "./shell-fallbacks";

import { PUBLIC_PAGE_FALLBACK_EN } from "./public-page-fallbacks";
import { SHELL_FALLBACK_EN } from "./shell-fallbacks";
import type { MessageCatalog } from "./core";

/** Static EN bootstrap for /login and /welcome (no API catalog fetch). */
export function buildPublicPageCatalogEn(): MessageCatalog {
  return { ...SHELL_FALLBACK_EN, ...PUBLIC_PAGE_FALLBACK_EN };
}
