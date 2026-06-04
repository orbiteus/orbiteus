"use client";

import { Center, Loader } from "@mantine/core";
import { DatesProvider } from "@mantine/dates";
import {
  buildPublicPageCatalogEn,
  I18nProvider,
  DAYJS_LOCALE,
  resolveDayjsLocale,
  useI18n,
} from "@orbiteus/i18n";
import "dayjs/locale/pl";
import "dayjs/locale/de";
import "dayjs/locale/fr";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { useUiLocales, useUiMessages } from "@/lib/queries/i18n";
import { useMemo } from "react";

const PUBLIC_PATHS = new Set(["/login", "/welcome"]);
const PUBLIC_PAGE_CATALOG_EN = buildPublicPageCatalogEn();

function DatesLocaleBridge({ children }: { children: React.ReactNode }) {
  const { locale } = useI18n();
  const dayjsLocale = resolveDayjsLocale(locale, DAYJS_LOCALE);
  return (
    <DatesProvider settings={{ locale: dayjsLocale, firstDayOfWeek: 1 }}>
      {children}
    </DatesProvider>
  );
}

export default function AdminI18nShell({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  const isPublicRoute = PUBLIC_PATHS.has(path);
  const { user, hydrated } = useAuth();
  const needsApiCatalog = hydrated && Boolean(user) && !isPublicRoute;

  const localesQuery = useUiLocales(needsApiCatalog);
  const guestLang =
    typeof window !== "undefined"
      ? window.localStorage.getItem("orbiteus.locale") ?? undefined
      : undefined;
  const activeLang = hydrated ? user?.language ?? guestLang ?? "en" : guestLang ?? "en";
  const messagesQuery = useUiMessages(activeLang, needsApiCatalog);

  const runtimeOverrides = useMemo(() => {
    if (isPublicRoute) {
      return { en: PUBLIC_PAGE_CATALOG_EN };
    }
    if (!messagesQuery.data || !activeLang) return undefined;
    return { [activeLang]: messagesQuery.data };
  }, [isPublicRoute, messagesQuery.data, activeLang]);

  const serverLocales = useMemo(
    () =>
      localesQuery.data?.map((row) => ({
        code: row.code,
        label: row.label,
        dayjsLocale: row.dayjs,
      })),
    [localesQuery.data],
  );

  const catalogLoading =
    needsApiCatalog && messagesQuery.isLoading && !messagesQuery.data;

  return (
    <I18nProvider
      userLanguage={hydrated ? user?.language : undefined}
      userTimezone={hydrated ? user?.timezone : undefined}
      serverLocales={serverLocales}
      runtimeOverrides={runtimeOverrides}
      waitForCatalog={needsApiCatalog}
    >
      {catalogLoading ? (
        <Center h="100vh">
          <Loader color="gray" size="sm" />
        </Center>
      ) : (
        <DatesLocaleBridge>{children}</DatesLocaleBridge>
      )}
    </I18nProvider>
  );
}
