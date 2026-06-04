"use client";

import { useMemo, useRef, useState } from "react";
import Link from "next/link";
import {
  ActionIcon,
  Button,
  FileButton,
  Group,
  Loader,
  Modal,
  Pagination,
  Paper,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
  Tooltip,
} from "@mantine/core";
import {
  IconDownload,
  IconPaperclip,
  IconRefresh,
  IconTrash,
  IconUpload,
} from "@tabler/icons-react";
import { notifications } from "@mantine/notifications";
import { useT } from "@orbiteus/i18n";
import {
  attachmentDownloadUrl,
  type AttachmentRow,
  useAttachments,
  useDeleteAttachment,
  usePurgeOrphanAttachments,
  useUploadAttachment,
} from "@/lib/queries/attachments";
import { apiErrorMessage, extractApiError } from "@/lib/api";
import { formatListDate } from "@/lib/formatters";
import { relationToResource } from "@/lib/relationPath";
import { useUiConfig } from "@/lib/queries/uiConfig";
import Many2OneField from "@/components/widgets/Many2OneField";

const PAGE_SIZE = 50;

function formatBytes(size: number): string {
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${Math.round(size / 1024)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

function recordHref(row: AttachmentRow): string | null {
  if (!row.res_model || !row.res_id) return null;
  const [module, model] = row.res_model.split(".");
  if (!module || !model) return null;
  return `/${module}/${model}/${row.res_id}`;
}

export default function TechnicalAttachmentsPage() {
  const t = useT();
  const [q, setQ] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [uploadModel, setUploadModel] = useState<string | null>(null);
  const [uploadRecordId, setUploadRecordId] = useState<string | null>(null);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const resetRef = useRef<() => void>(null);

  const uiConfig = useUiConfig();
  const modelOptions = useMemo(() => {
    const names = new Set<string>();
    for (const mod of uiConfig.data?.modules ?? []) {
      for (const m of mod.models) names.add(m.name);
    }
    return [...names].sort().map((value) => ({ value, label: value }));
  }, [uiConfig.data]);

  const offset = (page - 1) * PAGE_SIZE;
  const listQuery = useAttachments({ q: search || undefined, limit: PAGE_SIZE, offset });
  const uploadMutation = useUploadAttachment();
  const deleteMutation = useDeleteAttachment();
  const purgeMutation = usePurgeOrphanAttachments();

  const orphanCount = useMemo(
    () => (listQuery.data?.items ?? []).filter((r) => r.res_record_exists === false).length,
    [listQuery.data?.items],
  );

  const totalPages = Math.max(1, Math.ceil((listQuery.data?.total ?? 0) / PAGE_SIZE));

  function applySearch() {
    setSearch(q.trim());
    setPage(1);
  }

  async function submitUpload() {
    if (!uploadFile || !uploadModel || !uploadRecordId) return;
    try {
      await uploadMutation.mutateAsync({
        file: uploadFile,
        res_model: uploadModel,
        res_id: uploadRecordId,
      });
      setUploadOpen(false);
      setUploadFile(null);
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

  async function handlePurgeOrphans() {
    if (!window.confirm(t("attachments.purgeOrphansConfirm"))) return;
    try {
      const { removed } = await purgeMutation.mutateAsync();
      notifications.show({
        color: "green",
        message: t("attachments.purgedOrphans", { count: removed }),
      });
    } catch (err) {
      notifications.show({
        color: "red",
        title: t("attachments.purgeOrphansFailedTitle"),
        message: extractApiError(err, t("attachments.purgeOrphansFailed")),
      });
    }
  }

  async function handleDelete(row: AttachmentRow) {
    if (!window.confirm(t("attachments.deleteConfirm", { name: row.name }))) return;
    try {
      await deleteMutation.mutateAsync(row.id);
      notifications.show({ color: "green", message: t("attachments.deleted") });
    } catch (err) {
      notifications.show({
        color: "red",
        title: t("attachments.deleteFailedTitle"),
        message: extractApiError(err, t("attachments.deleteFailed")),
      });
    }
  }

  return (
    <Stack gap="md">
      <Group justify="space-between" align="flex-end">
        <div>
          <Title order={2}>{t("nav.technical.attachments")}</Title>
          <Text c="dimmed" size="sm">
            {t("attachments.catalogDescription")}
          </Text>
        </div>
        <Group>
          {orphanCount > 0 ? (
            <Button
              variant="light"
              color="orange"
              loading={purgeMutation.isPending}
              onClick={() => void handlePurgeOrphans()}
            >
              {t("attachments.purgeOrphans", { count: orphanCount })}
            </Button>
          ) : null}
          <Button
            leftSection={<IconRefresh size={16} />}
            variant="default"
            onClick={() => void listQuery.refetch()}
          >
            {t("common.refresh")}
          </Button>
          <Button
            leftSection={<IconUpload size={16} />}
            onClick={() => setUploadOpen(true)}
          >
            {t("attachments.upload")}
          </Button>
        </Group>
      </Group>

      <Paper withBorder p="md">
        <Group align="flex-end">
          <TextInput
            label={t("attachments.searchName")}
            placeholder={t("attachments.searchPlaceholder")}
            value={q}
            onChange={(e) => setQ(e.currentTarget.value)}
            onKeyDown={(e) => e.key === "Enter" && applySearch()}
            style={{ flex: 1 }}
          />
          <Button onClick={applySearch}>{t("common.searchButton")}</Button>
        </Group>
      </Paper>

      <Paper withBorder p="md">
        {listQuery.isLoading ? (
          <Group justify="center" p="xl"><Loader /></Group>
        ) : listQuery.isError ? (
          <Text c="red">{extractApiError(listQuery.error, t("attachments.loadFailed"))}</Text>
        ) : (
          <>
            <Table striped highlightOnHover withTableBorder>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>{t("attachments.name")}</Table.Th>
                  <Table.Th>{t("attachments.linkedRecord")}</Table.Th>
                  <Table.Th>{t("attachments.size")}</Table.Th>
                  <Table.Th>{t("attachments.uploadedAt")}</Table.Th>
                  <Table.Th w={90} />
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {(listQuery.data?.items ?? []).map((row) => {
                  const href =
                    row.res_record_exists !== false ? recordHref(row) : null;
                  return (
                    <Table.Tr key={row.id}>
                      <Table.Td>{row.name}</Table.Td>
                      <Table.Td>
                        {href ? (
                          <Text
                            component={Link}
                            href={href}
                            size="sm"
                            c="blue"
                          >
                            {row.res_model} / {row.res_id?.slice(0, 8)}…
                          </Text>
                        ) : row.res_model && row.res_id ? (
                          <Tooltip label={t("attachments.recordMissing")}>
                            <Text size="sm" c="dimmed">
                              {row.res_model} / {row.res_id.slice(0, 8)}… ({t("attachments.recordMissingShort")})
                            </Text>
                          </Tooltip>
                        ) : (
                          <Text size="sm" c="dimmed">{row.res_model || t("common.dash")}</Text>
                        )}
                      </Table.Td>
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
                          <Tooltip label={t("common.delete")}>
                            <ActionIcon
                              variant="subtle"
                              color="red"
                              onClick={() => void handleDelete(row)}
                            >
                              <IconTrash size={16} />
                            </ActionIcon>
                          </Tooltip>
                        </Group>
                      </Table.Td>
                    </Table.Tr>
                  );
                })}
              </Table.Tbody>
            </Table>
            {(listQuery.data?.total ?? 0) > PAGE_SIZE ? (
              <Group justify="center" mt="md">
                <Pagination total={totalPages} value={page} onChange={setPage} />
              </Group>
            ) : null}
          </>
        )}
      </Paper>

      <Modal
        opened={uploadOpen}
        onClose={() => setUploadOpen(false)}
        title={t("attachments.uploadAttachment")}
        size="lg"
      >
        <Stack gap="md">
          <Select
            label={t("attachments.targetModel")}
            data={modelOptions}
            value={uploadModel}
            onChange={(v) => {
              setUploadModel(v);
              setUploadRecordId(null);
            }}
            searchable
            nothingFoundMessage={t("attachments.noModels")}
          />
          {uploadModel ? (
            <Many2OneField
              label={t("attachments.targetRecord")}
              relation={relationToResource(uploadModel)}
              value={uploadRecordId}
              onChange={setUploadRecordId}
              required
            />
          ) : null}
          <Group>
            <FileButton onChange={setUploadFile} resetRef={resetRef}>
              {(props) => (
                <Button {...props} variant="default" leftSection={<IconPaperclip size={16} />}>
                  {uploadFile ? t("attachments.changeFile") : t("attachments.pickFile")}
                </Button>
              )}
            </FileButton>
            {uploadFile ? (
              <Text size="sm">{uploadFile.name} ({formatBytes(uploadFile.size)})</Text>
            ) : null}
          </Group>
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setUploadOpen(false)}>{t("common.cancel")}</Button>
            <Button
              loading={uploadMutation.isPending}
              disabled={!uploadFile || !uploadModel || !uploadRecordId}
              onClick={() => void submitUpload()}
            >
              {t("attachments.upload")}
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Stack>
  );
}
