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
import { shouldBlockAuthenticatedShell } from "@/lib/i18nShellGate";
import { useUiLocales, useUiMessages } from "@/lib/queries/i18n";
import { useMemo } from "react";

const PUBLIC_PATHS = new Set(["/login", "/welcome"]);
const PUBLIC_PAGE_CATALOG_EN = buildPublicPageCatalogEn();

function DatesLocaleBridge({ children }: { children: React.ReactNode }) {
  const { locale } = useI18n();
  const dayjsLocale = resolveDayjsLocale(locale, DAYJS_LOCALE);
  const dateSettings = useMemo(
    () => ({ locale: dayjsLocale, firstDayOfWeek: 1 as const }),
    [dayjsLocale],
  );
  return <DatesProvider settings={dateSettings}>{children}</DatesProvider>;
}

export default function AdminI18nShell({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  const isPublicRoute = PUBLIC_PATHS.has(path);
  const isAuthenticatedShell = !isPublicRoute;
  const { user, hydrated } = useAuth();

  const localesQuery = useUiLocales(isAuthenticatedShell);
  const guestLang =
    typeof window !== "undefined"
      ? window.localStorage.getItem("orbiteus.locale") ?? undefined
      : undefined;
  const activeLang = hydrated ? user?.language ?? guestLang ?? "en" : guestLang ?? "en";
  const messagesQuery = useUiMessages(activeLang, isAuthenticatedShell);

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

  const shellBlocked = shouldBlockAuthenticatedShell({
    isPublicRoute,
    hydrated,
    hasCatalog: Boolean(messagesQuery.data),
  });

  return (
    <I18nProvider
      userLanguage={hydrated ? user?.language : undefined}
      userTimezone={hydrated ? user?.timezone : undefined}
      serverLocales={serverLocales}
      runtimeOverrides={runtimeOverrides}
      waitForCatalog={isAuthenticatedShell}
    >
      {shellBlocked ? (
        <Center h="100vh">
          <Loader color="gray" size="sm" />
        </Center>
      ) : (
        <DatesLocaleBridge>{children}</DatesLocaleBridge>
      )}
    </I18nProvider>
  );
}
