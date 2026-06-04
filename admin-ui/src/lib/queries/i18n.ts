"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchUiLocales, fetchUiMessages, type UiLocaleMeta } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";
import type { UiLanguage } from "@orbiteus/i18n";

export function useUiLocales(enabled = true) {
  return useQuery({
    queryKey: queryKeys.i18nLocales(),
    queryFn: fetchUiLocales,
    enabled,
    staleTime: 300_000,
    refetchOnWindowFocus: false,
  });
}

export function useUiMessages(lang: UiLanguage | string | undefined, enabled = true) {
  const code = lang ?? "en";
  return useQuery({
    queryKey: queryKeys.i18nMessages(code),
    queryFn: () => fetchUiMessages(code),
    enabled: enabled && Boolean(lang),
    staleTime: 300_000,
    gcTime: 600_000,
    placeholderData: (previousData) => previousData,
    refetchOnWindowFocus: false,
  });
}

export type { UiLocaleMeta };
