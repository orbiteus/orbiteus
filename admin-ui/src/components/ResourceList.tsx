"use client";
import { useEffect, useState, useRef, useCallback, useMemo } from "react";
import { useQueryClient } from "@tanstack/react-query";
import type { FieldMeta } from "@/lib/api";
import { prefetchResourceDetail, useResourceList } from "@/lib/queries/resources";
import { StatusBadge } from "@/components/widgets/StatusBadge";
import { LastLoginCell } from "@/components/widgets/LastLoginCell";
import { displayMany2oneCell, formatListDate } from "@/lib/formatters";
import { useI18n, DAYJS_LOCALE, resolveDayjsLocale } from "@orbiteus/i18n";
import { MonetaryCell } from "@/components/widgets/MonetaryField";
import EmptyState from "@/components/EmptyState";
import RecordRowSkeleton from "@/components/RecordRowSkeleton";
import RecordRowList from "@/components/RecordRowList";
import Link from "next/link";
import {
  Title, Text, Button, Alert, Group, Stack,
  Modal, Pagination, TextInput, Paper,
} from "@mantine/core";
import {
  IconPlus, IconAlertCircle, IconTrash, IconSearch,
} from "@tabler/icons-react";
import { notifications } from "@mantine/notifications";
import { extractApiError } from "@/lib/api";
import { useDeleteRecord } from "@/lib/queries/mutations";
import { useRealtimeList } from "@/lib/realtime";

interface Column {
  key: string;
  label: string;
  widget?: string;
  render?: (value: unknown, row: Record<string, unknown>) => React.ReactNode;
}

interface Props {
  title: string;
  resource: string;
  columns: Column[];
  fieldMeta?: FieldMeta[];
  createHref?: string;
  editHref?: (id: string) => string;
  pageSize?: number;
  /** When a page header already shows the title, hide the duplicate here. */
  showTitle?: boolean;
  /** Many2one fields to prefetch on row hover (form expand). */
  prefetchExpandFields?: string[];
}

type SortDir = "asc" | "desc" | null;

function useEnhancedColumns(columns: Column[], fieldMeta?: FieldMeta[]): Column[] {
  const { locale, t } = useI18n();
  const dayjsLocale = resolveDayjsLocale(locale, DAYJS_LOCALE);
  return useMemo(() => {
    if (!fieldMeta?.length) return columns;
    const meta = new Map(fieldMeta.map((f) => [f.name, f]));
    return columns.map((col) => {
      if (col.render) return col;
      const m = meta.get(col.key);
      if (col.widget === "badge" || col.key === "status") {
        return {
          ...col,
          render: (v: unknown) => <StatusBadge value={String(v ?? "")} />,
        };
      }
      if (col.widget === "last_login") {
        return {
          ...col,
          render: (_v: unknown, row: Record<string, unknown>) => (
            <LastLoginCell lastLogin={row.last_login} device={row.last_login_device} />
          ),
        };
      }
      if (m?.type === "monetary") {
        return {
          ...col,
          render: (v: unknown) => (
            <MonetaryCell value={v} currencyCode={m.currency_code} />
          ),
        };
      }
      if (m?.type === "many2one") {
        return {
          ...col,
          render: (_v: unknown, row: Record<string, unknown>) => displayMany2oneCell(row, col.key),
        };
      }
      if (m?.type === "date" || col.key.endsWith("_date") || col.key === "create_date") {
        return { ...col, render: (v: unknown) => formatListDate(v, dayjsLocale) };
      }
      return col;
    });
  }, [columns, fieldMeta, dayjsLocale, t]);
}

function visibleListColumns(columns: Column[]): Column[] {
  const hidden = new Set([
    "id", "tenant_id", "company_id", "created_by", "updated_by",
    "password", "password_hash", "recovery_codes_hashed",
  ]);
  return columns.filter((col) => !hidden.has(col.key)).slice(0, 5);
}

export default function ResourceList({
  title,
  resource,
  columns,
  fieldMeta,
  createHref,
  editHref,
  pageSize = 50,
  showTitle = true,
  prefetchExpandFields = [],
}: Props) {
  const qc = useQueryClient();
  const { t } = useI18n();
  const displayColumns = useEnhancedColumns(columns, fieldMeta);
  const listColumns = useMemo(
    () => visibleListColumns(displayColumns),
    [displayColumns],
  );

  const [page, setPage] = useState(1);
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const deleteMutation = useDeleteRecord(resource);
  const deleting = deleteMutation.isPending;

  const [searchInput, setSearchInput] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [orderBy, setOrderBy] = useState<string | null>(null);
  const [orderDir, setOrderDir] = useState<SortDir>(null);

  const handleSearchChange = useCallback((value: string) => {
    setSearchInput(value);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setSearchQuery(value);
      setPage(1);
    }, 300);
  }, []);

  useEffect(() => () => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
  }, []);

  const expandFields = useMemo(() => {
    if (!fieldMeta?.length) return "";
    const m2o = listColumns
      .map((col) => fieldMeta.find((f) => f.name === col.key))
      .filter((f) => f?.type === "many2one")
      .map((f) => f!.name);
    return m2o.join(",");
  }, [listColumns, fieldMeta]);

  const listParams = useMemo(() => {
    const params: Record<string, unknown> = {
      limit: pageSize,
      offset: (page - 1) * pageSize,
    };
    if (searchQuery) {
      const searchField = listColumns[0]?.key ?? "name";
      params[`${searchField}__contains`] = searchQuery;
    }
    if (orderBy && orderDir) {
      params.order_by = orderBy;
      params.order_dir = orderDir;
    }
    if (expandFields) params.expand = expandFields;
    return params;
  }, [page, pageSize, searchQuery, orderBy, orderDir, expandFields, listColumns]);

  const listQuery = useResourceList(resource, listParams);
  const items = listQuery.data?.items ?? [];
  const total = listQuery.data?.total ?? 0;
  const loading = listQuery.isLoading && !listQuery.data;
  const error = listQuery.isError
    ? (listQuery.error instanceof Error ? listQuery.error.message : t("request.failed"))
    : "";

  useRealtimeList(resource, () => {
    void qc.invalidateQueries({ queryKey: ["resource", "list", resource] });
  });

  const handlePrefetchRow = useCallback(
    (id: string) => {
      if (!prefetchExpandFields.length) return;
      void prefetchResourceDetail(qc, resource, id, prefetchExpandFields);
    },
    [qc, resource, prefetchExpandFields],
  );

  const filteredItems = useMemo(() => {
    if (!searchQuery) return items;
    const q = searchQuery.toLowerCase();
    return items.filter((row) =>
      displayColumns.some((col) => {
        const val = row[col.key];
        return val != null && String(val).toLowerCase().includes(q);
      })
    );
  }, [items, searchQuery, displayColumns]);

  function handleSort(columnKey: string) {
    if (orderBy !== columnKey) {
      setOrderBy(columnKey);
      setOrderDir("asc");
    } else if (orderDir === "asc") {
      setOrderDir("desc");
    } else {
      setOrderBy(null);
      setOrderDir(null);
    }
    setPage(1);
  }

  async function handleDelete() {
    if (!deleteId) return;
    try {
      await deleteMutation.mutateAsync(deleteId);
      notifications.show({ title: t("form.deleted"), message: t("list.deleted"), color: "orange" });
    } catch (e: unknown) {
      notifications.show({
        title: t("common.error"),
        message: extractApiError(e, t("form.deleteFailed")),
        color: "red",
      });
    } finally {
      setDeleteId(null);
    }
  }

  const totalPages = Math.ceil(total / pageSize);

  return (
    <>
      <Stack gap="sm">
        {showTitle && (
          <Title order={3} fw={600}>
            {title}
          </Title>
        )}

        <Group justify="space-between" align="center" wrap="nowrap" gap="sm">
          <TextInput
            placeholder={t("list.search")}
            leftSection={<IconSearch size={16} stroke={1.75} />}
            value={searchInput}
            onChange={(e) => handleSearchChange(e.currentTarget.value)}
            radius="md"
            style={{ flex: 1, maxWidth: 380 }}
          />
          <Group gap="sm" wrap="nowrap">
            {!loading && (
              <Text size="sm" c="dimmed" style={{ whiteSpace: "nowrap" }}>
                {total} {total === 1 ? t("list.record") : t("list.records")}
              </Text>
            )}
            {createHref && (
              <Button
                component={Link}
                href={createHref}
                leftSection={<IconPlus size={16} />}
                radius="md"
              >
                New
              </Button>
            )}
          </Group>
        </Group>

        {error && <Alert icon={<IconAlertCircle size={16} />} color="red" title={t("common.error")}>{error}</Alert>}

        {!error && (
          <>
            {loading ? (
              <RecordRowSkeleton rows={10} />
            ) : filteredItems.length === 0 ? (
              <Paper p="lg" radius="md" withBorder>
                <EmptyState
                  title={searchQuery ? t("list.noMatches") : t("list.noRecords")}
                  description={
                    searchQuery
                      ? t("list.noMatchesHint")
                      : t("list.emptyHint")
                  }
                  ctaLabel={createHref ? t("list.new") : undefined}
                  ctaHref={createHref}
                  py="md"
                />
              </Paper>
            ) : (
              <RecordRowList
                rows={filteredItems}
                columns={listColumns}
                editHref={editHref}
                onDelete={setDeleteId}
                onRowHover={handlePrefetchRow}
                orderBy={orderBy}
                orderDir={orderDir}
                onSort={handleSort}
              />
            )}

            {totalPages > 1 && (
              <Pagination value={page} onChange={setPage} total={totalPages}
                styles={{ root: { justifyContent: "flex-end" } }} />
            )}
          </>
        )}
      </Stack>

      <Modal
        opened={Boolean(deleteId)} onClose={() => setDeleteId(null)}
        title={t("list.deleteTitle")} size="sm"
      >
        <Stack gap="md">
          <Text size="sm" c="dimmed">{t("list.deleteConfirm")}</Text>
          <Group justify="flex-end">
            <Button variant="subtle" color="gray" onClick={() => setDeleteId(null)}>{t("common.cancel")}</Button>
            <Button color="red" loading={deleting} onClick={handleDelete} leftSection={<IconTrash size={16} />}>
              {t("common.delete")}
            </Button>
          </Group>
        </Stack>
      </Modal>
    </>
  );
}
