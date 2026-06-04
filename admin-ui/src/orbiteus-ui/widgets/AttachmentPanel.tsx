"use client";

import { useRef, useState } from "react";
import {
  ActionIcon,
  Button,
  FileButton,
  Group,
  Paper,
  Stack,
  Table,
  Text,
  Tooltip,
} from "@mantine/core";
import { IconDownload, IconPaperclip, IconTrash } from "@tabler/icons-react";
import { notifications } from "@mantine/notifications";
import { useT } from "@orbiteus/i18n";
import {
  attachmentDownloadUrl,
  useAttachments,
  useDeleteAttachment,
  useUploadAttachment,
} from "@/lib/queries/attachments";
import { apiErrorMessage, extractApiError } from "@/lib/api";
import { formatListDate } from "@/lib/formatters";

function formatBytes(size: number): string {
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${Math.round(size / 1024)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

export interface AttachmentPanelProps {
  resModel: string;
  resId: string;
  readOnly?: boolean;
  title?: string;
}

/** Record-scoped attachment list + upload (framework widget). */
export function AttachmentPanel({
  resModel,
  resId,
  readOnly = false,
  title = "Attachments",
}: AttachmentPanelProps) {
  const t = useT();
  const resetRef = useRef<() => void>(null);
  const [file, setFile] = useState<File | null>(null);
  const listQuery = useAttachments({ res_model: resModel, res_id: resId, limit: 100 });
  const uploadMutation = useUploadAttachment();
  const deleteMutation = useDeleteAttachment();

  async function handleUpload() {
    if (!file) return;
    try {
      await uploadMutation.mutateAsync({
        file,
        res_model: resModel,
        res_id: resId,
      });
      setFile(null);
      resetRef.current?.();
      notifications.show({ color: "green", message: t("attachments.uploaded") });
    } catch (err) {
      notifications.show({
        color: "red",
        title: t("attachments.uploadFailedTitle"),
        message: apiErrorMessage(err, extractApiError(err, t("attachments.uploadFailed"))),
      });
    }
  }

  async function handleDelete(id: string, name: string) {
    if (!window.confirm(t("attachments.deleteConfirm", { name }))) return;
    try {
      await deleteMutation.mutateAsync(id);
      notifications.show({ color: "green", message: t("attachments.deleted") });
    } catch (err) {
      notifications.show({
        color: "red",
        title: t("attachments.deleteFailedTitle"),
        message: extractApiError(err, t("attachments.deleteFailed")),
      });
    }
  }

  const rows = listQuery.data?.items ?? [];

  return (
    <Paper withBorder p="md">
      <Stack gap="sm">
        <Text fw={600}>{title}</Text>

        {!readOnly ? (
          <Group align="flex-end">
            <FileButton onChange={setFile} resetRef={resetRef}>
              {(props) => (
                <Button {...props} variant="default" leftSection={<IconPaperclip size={16} />}>
                  {file ? t("attachments.changeFile") : t("attachments.pickFile")}
                </Button>
              )}
            </FileButton>
            {file ? <Text size="sm">{file.name} ({formatBytes(file.size)})</Text> : null}
            <Button
              onClick={handleUpload}
              loading={uploadMutation.isPending}
              disabled={!file}
            >
              {t("attachments.upload")}
            </Button>
          </Group>
        ) : null}

        {listQuery.isLoading ? (
          <Text size="sm" c="dimmed">{t("attachments.loading")}</Text>
        ) : rows.length === 0 ? (
          <Text size="sm" c="dimmed">{t("attachments.empty")}</Text>
        ) : (
          <Table striped highlightOnHover withTableBorder>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>{t("attachments.name")}</Table.Th>
                <Table.Th>{t("attachments.size")}</Table.Th>
                <Table.Th>{t("attachments.uploadedAt")}</Table.Th>
                <Table.Th w={80} />
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {rows.map((row) => (
                <Table.Tr key={row.id}>
                  <Table.Td>{row.name}</Table.Td>
                  <Table.Td>{formatBytes(row.file_size)}</Table.Td>
                  <Table.Td>{formatListDate(row.create_date)}</Table.Td>
                  <Table.Td>
                    <Group gap={4} wrap="nowrap">
                      <Tooltip label={t("attachments.download")}>
                        <ActionIcon
                          component="a"
                          href={attachmentDownloadUrl(row.id)}
                          variant="subtle"
                        >
                          <IconDownload size={16} />
                        </ActionIcon>
                      </Tooltip>
                      {!readOnly ? (
                        <Tooltip label={t("common.delete")}>
                          <ActionIcon
                            variant="subtle"
                            color="red"
                            loading={deleteMutation.isPending}
                            onClick={() => void handleDelete(row.id, row.name)}
                          >
                            <IconTrash size={16} />
                          </ActionIcon>
                        </Tooltip>
                      ) : null}
                    </Group>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        )}
      </Stack>
    </Paper>
  );
}
