"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";

export interface AttachmentRow {
  id: string;
  tenant_id: string | null;
  name: string;
  res_model: string;
  res_id: string | null;
  mimetype: string;
  file_size: number;
  description: string;
  create_date: string | null;
  created_by_id: string | null;
  /** False when the linked business record was deleted (e.g. after demo reset). */
  res_record_exists?: boolean;
}

export interface AttachmentListPage {
  items: AttachmentRow[];
  total: number;
  limit: number;
  offset: number;
}

export interface AttachmentListParams {
  q?: string;
  res_model?: string;
  res_id?: string;
  limit?: number;
  offset?: number;
}

export async function fetchAttachments(
  params: AttachmentListParams = {},
): Promise<AttachmentListPage> {
  const { data } = await api.get<AttachmentListPage>("/base/attachments", { params });
  return data;
}

export async function uploadAttachment(input: {
  file: File;
  res_model: string;
  res_id: string;
  description?: string;
}): Promise<AttachmentRow> {
  const form = new FormData();
  form.append("file", input.file);
  form.append("res_model", input.res_model);
  form.append("res_id", input.res_id);
  if (input.description) form.append("description", input.description);
  const { data } = await api.post<AttachmentRow>("/base/attachments", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function deleteAttachment(id: string): Promise<void> {
  await api.delete(`/base/attachments/${id}`);
}

export function attachmentDownloadUrl(id: string): string {
  return `/api/base/attachments/${id}/download`;
}

export function useAttachments(params: AttachmentListParams, enabled = true) {
  return useQuery({
    queryKey: queryKeys.attachments(params),
    queryFn: () => fetchAttachments(params),
    enabled,
  });
}

export function useUploadAttachment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: uploadAttachment,
    onSuccess: (_data, vars) => {
      void qc.invalidateQueries({ queryKey: ["attachments"] });
      if (vars.res_model && vars.res_id) {
        void qc.invalidateQueries({
          queryKey: queryKeys.attachments({
            res_model: vars.res_model,
            res_id: vars.res_id,
          }),
        });
      }
    },
  });
}

export function useDeleteAttachment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: deleteAttachment,
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["attachments"] });
    },
  });
}

export async function purgeOrphanAttachments(): Promise<{ removed: number }> {
  const { data } = await api.post<{ status: string; removed: number }>(
    "/base/attachments/purge-orphans",
  );
  return { removed: data.removed };
}

export function usePurgeOrphanAttachments() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: purgeOrphanAttachments,
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["attachments"] });
    },
  });
}
