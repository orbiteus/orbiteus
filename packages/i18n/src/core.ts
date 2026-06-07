/** Built-in UI locales shipped with Orbiteus core. */
import { SHELL_FALLBACK_EN } from "./shell-fallbacks";

export type KnownUiLanguage = "en" | "pl" | "de" | "fr";

/** Any registered locale code (built-in or module / DB extension). */
export type UiLanguage = KnownUiLanguage | (string & {});

export const SUPPORTED_UI_LANGUAGES: readonly KnownUiLanguage[] = ["en", "pl", "de", "fr"] as const;

export const DEFAULT_UI_LANGUAGE: UiLanguage = "en";

export const LANGUAGE_LABELS: Record<UiLanguage, string> = {
  en: "English",
  pl: "Polski",
  de: "Deutsch",
  fr: "Français",
};

/** Mantine / dayjs locale codes derived from UI language. */
export const DAYJS_LOCALE: Record<UiLanguage, string> = {
  en: "en",
  pl: "pl",
  de: "de",
  fr: "fr",
};

export const COMMON_TIMEZONES = [
  "UTC",
  "Europe/Warsaw",
  "Europe/Berlin",
  "Europe/Paris",
  "Europe/London",
  "America/New_York",
  "America/Chicago",
  "America/Los_Angeles",
  "Asia/Tokyo",
  "Asia/Singapore",
  "Australia/Sydney",
] as const;

export type MessageCatalog = Record<string, string>;

export type TranslateVars = Record<string, string | number>;

export function isKnownUiLanguage(value: string | null | undefined): value is KnownUiLanguage {
  return SUPPORTED_UI_LANGUAGES.includes(value as KnownUiLanguage);
}

/** @deprecated Use isKnownUiLanguage for built-ins only. */
export function isUiLanguage(value: string | null | undefined): value is KnownUiLanguage {
  return isKnownUiLanguage(value);
}

export function normalizeUiLanguage(
  value: string | null | undefined,
  fallback: UiLanguage = DEFAULT_UI_LANGUAGE,
  extraCodes?: Iterable<string>,
): UiLanguage {
  const raw = (value ?? "").trim().toLowerCase();
  const extras = extraCodes ? new Set(extraCodes) : null;
  if (extras?.has(raw)) return raw;
  if (isKnownUiLanguage(raw)) return raw;
  if (raw.startsWith("pl")) return "pl";
  if (raw.startsWith("de")) return "de";
  if (raw.startsWith("fr")) return "fr";
  if (raw.startsWith("en")) return "en";
  return fallback;
}

export function detectBrowserLanguage(): UiLanguage {
  if (typeof navigator === "undefined") return DEFAULT_UI_LANGUAGE;
  return normalizeUiLanguage(navigator.language, DEFAULT_UI_LANGUAGE);
}

export function createTranslator(
  locale: UiLanguage,
  catalogs: Record<string, MessageCatalog>,
) {
  const primary = catalogs[locale] ?? {};
  const fallback = catalogs.en ?? catalogs[DEFAULT_UI_LANGUAGE] ?? {};

  function t(key: string, vars?: TranslateVars): string {
    let msg =
      primary[key] ??
      fallback[key] ??
      SHELL_FALLBACK_EN[key] ??
      key;
    if (!vars) return msg;
    for (const [name, value] of Object.entries(vars)) {
      msg = msg.replace(new RegExp(`\\{${name}\\}`, "g"), String(value));
    }
    return msg;
  }

  return { locale, t };
}

export type Translator = ReturnType<typeof createTranslator>;
