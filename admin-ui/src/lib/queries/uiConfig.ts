"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchUiConfig, type UiConfig } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";

export function useUiConfig(enabled = true) {
  return useQuery({
    queryKey: queryKeys.uiConfig(),
    queryFn: fetchUiConfig,
    enabled,
    staleTime: 60_000,
    refetchOnWindowFocus: false,
  });
}

export function useUiConfigModel(mod: string, model: string) {
  const q = useUiConfig();
  const key = `${mod}.${model}`;
  const modelCfg =
    q.data?.modules
      .find((m) => m.name === mod)
      ?.models.find((m) => m.name === key) ?? null;
  return { ...q, model: modelCfg };
}

export type { UiConfig };
