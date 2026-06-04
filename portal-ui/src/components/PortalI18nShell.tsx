"use client";

import { buildPublicPageCatalogEn, I18nProvider } from "@orbiteus/i18n";
import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { fetchUiLocales, fetchUiMessages } from "@/lib/api";

const LOCALE_STORAGE_KEY = "orbiteus.locale";
const PUBLIC_PAGE_CATALOG_EN = buildPublicPageCatalogEn();

function guestLanguage(): string {
  if (typeof window === "undefined") return "en";
  return window.localStorage.getItem(LOCALE_STORAGE_KEY) ?? "en";
}

export default function PortalI18nShell({ children }: { children: React.ReactNode }) {
  const lang = guestLanguage();

  const localesQuery = useQuery({
    queryKey: ["i18n", "locales"],
    queryFn: fetchUiLocales,
    staleTime: 300_000,
    refetchOnWindowFocus: false,
  });

  const messagesQuery = useQuery({
    queryKey: ["i18n", "messages", lang],
    queryFn: () => fetchUiMessages(lang),
    staleTime: 300_000,
    gcTime: 600_000,
    placeholderData: (previous) => previous,
    refetchOnWindowFocus: false,
  });

  const runtimeOverrides = useMemo(() => {
    if (messagesQuery.data) {
      return { [lang]: messagesQuery.data };
    }
    return { en: PUBLIC_PAGE_CATALOG_EN };
  }, [messagesQuery.data, lang]);

  const serverLocales = useMemo(
    () =>
      localesQuery.data?.map((row) => ({
        code: row.code,
        label: row.label,
        dayjsLocale: row.dayjs,
      })),
    [localesQuery.data],
  );

  return (
    <I18nProvider
      serverLocales={serverLocales}
      runtimeOverrides={runtimeOverrides}
      waitForCatalog={false}
    >
      {children}
    </I18nProvider>
  );
}
