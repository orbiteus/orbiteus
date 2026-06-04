"use client";

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  createTranslator,
  detectBrowserLanguage,
  normalizeUiLanguage,
  type Translator,
  type UiLanguage,
} from "./core";
import {
  buildRuntimeCatalogs,
  getRegisteredLanguageCodes,
  registerLocaleMeta,
  type LocaleMeta,
} from "./registry";

export type I18nContextValue = Translator & {
  timezone: string;
  setLanguage: (language: UiLanguage) => void;
  /** False until API catalog for the active locale is merged (when overrides supplied). */
  ready: boolean;
};

const I18nContext = createContext<I18nContextValue | null>(null);

const LOCALE_STORAGE_KEY = "orbiteus.locale";

export type I18nProviderProps = {
  children: ReactNode;
  userLanguage?: string | null;
  userTimezone?: string | null;
  /** Merged catalog from GET /api/base/i18n/messages/{lang} — required for translated UI. */
  runtimeOverrides?: Partial<Record<string, Record<string, string>>>;
  serverLocales?: LocaleMeta[];
  /** When true, children render only after runtimeOverrides include the active locale. */
  waitForCatalog?: boolean;
};

export function I18nProvider({
  children,
  userLanguage,
  userTimezone,
  runtimeOverrides,
  serverLocales,
  waitForCatalog = false,
}: I18nProviderProps) {
  useEffect(() => {
    if (serverLocales?.length) {
      registerLocaleMeta(serverLocales);
    }
  }, [serverLocales]);

  const registeredCodes = useMemo(
    () => getRegisteredLanguageCodes(),
    [serverLocales, runtimeOverrides],
  );

  const catalogs = useMemo(
    () => buildRuntimeCatalogs(runtimeOverrides),
    [runtimeOverrides],
  );

  const [guestLanguage, setGuestLanguage] = useState<UiLanguage>(() => {
    if (typeof window === "undefined") return "en";
    const stored = window.localStorage.getItem(LOCALE_STORAGE_KEY);
    return normalizeUiLanguage(stored ?? detectBrowserLanguage(), "en", registeredCodes);
  });

  const language = useMemo(
    () => normalizeUiLanguage(userLanguage ?? guestLanguage, "en", registeredCodes),
    [userLanguage, guestLanguage, registeredCodes],
  );

  const timezone = userTimezone?.trim() || "UTC";

  const ready = !waitForCatalog || Boolean(runtimeOverrides?.[language]);

  const setLanguage = useCallback(
    (next: UiLanguage) => {
      setGuestLanguage(next);
      if (typeof window !== "undefined") {
        window.localStorage.setItem(LOCALE_STORAGE_KEY, next);
      }
    },
    [],
  );

  useEffect(() => {
    if (typeof document !== "undefined") {
      document.documentElement.lang = language;
    }
  }, [language]);

  const value = useMemo((): I18nContextValue => {
    const base = createTranslator(language, catalogs);
    return { ...base, timezone, setLanguage, ready };
  }, [language, timezone, setLanguage, catalogs, ready]);

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18nContextValue {
  const ctx = useContext(I18nContext);
  const catalogs = useMemo(() => buildRuntimeCatalogs(), []);
  if (!ctx) {
    return {
      ...createTranslator("en", catalogs),
      timezone: "UTC",
      setLanguage: () => {},
      ready: true,
    };
  }
  return ctx;
}

export function useT(): I18nContextValue["t"] {
  return useI18n().t;
}
