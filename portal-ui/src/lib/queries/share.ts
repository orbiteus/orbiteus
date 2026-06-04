"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  fetchShareView,
  postPortalAttachment,
  postPortalComment,
  type ShareResourceView,
} from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";

export function useShareResourceView(token: string) {
  return useQuery({
    queryKey: queryKeys.shareView(token),
    queryFn: () => fetchShareView(token),
    placeholderData: (prev) => prev,
  });
}

export function usePortalComment(token: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: string) => postPortalComment(token, body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: queryKeys.shareView(token) });
    },
  });
}

export function usePortalAttachment(token: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => postPortalAttachment(token, file),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: queryKeys.shareView(token) });
    },
  });
}

export type { ShareResourceView };
