"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { createRecord, deleteRecord, updateRecord } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";

export function useCreateRecord(resource: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: unknown) => createRecord(resource, payload),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["resource", "list", resource] });
    },
  });
}

export function useUpdateRecord(resource: string, recordId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: unknown) => {
      if (!recordId) throw new Error("Missing record id");
      return updateRecord(resource, recordId, payload);
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["resource", "list", resource] });
      if (recordId) {
        void qc.invalidateQueries({
          queryKey: queryKeys.resourceDetail(resource, recordId),
        });
      }
    },
  });
}

export function useDeleteRecord(resource: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteRecord(resource, id),
    onSuccess: (_data, id) => {
      void qc.invalidateQueries({ queryKey: ["resource", "list", resource] });
      void qc.removeQueries({ queryKey: queryKeys.resourceDetail(resource, id) });
    },
  });
}
