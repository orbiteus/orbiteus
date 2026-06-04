"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchList, fetchOne, type ListResponse } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";

export function useResourceList<T = Record<string, unknown>>(
  resource: string,
  params: Record<string, unknown>,
  enabled = true,
) {
  return useQuery({
    queryKey: queryKeys.resourceList(resource, params),
    queryFn: () => fetchList<T>(resource, params),
    enabled,
    placeholderData: (prev) => prev,
  });
}

export function useResourceDetail(
  resource: string,
  id: string | undefined,
  expandFields: string[],
) {
  const expand = expandFields.length > 0 ? expandFields.join(",") : undefined;
  return useQuery({
    queryKey: queryKeys.resourceDetail(resource, id ?? "", expand),
    queryFn: () => fetchOne(resource, id!, expand ? { expand } : undefined),
    enabled: Boolean(id),
    placeholderData: (prev) => prev,
  });
}

export function prefetchResourceDetail(
  qc: ReturnType<typeof useQueryClient>,
  resource: string,
  id: string,
  expandFields: string[],
) {
  const expand = expandFields.length > 0 ? expandFields.join(",") : undefined;
  return qc.prefetchQuery({
    queryKey: queryKeys.resourceDetail(resource, id, expand),
    queryFn: () => fetchOne(resource, id, expand ? { expand } : undefined),
    staleTime: 60_000,
  });
}

export type { ListResponse };
