"use client";
import { useEffect, useState, useRef, useCallback, useMemo } from "react";
import type { FieldMeta } from "@/lib/api";
import { StatusBadge } from "@/components/widgets/StatusBadge";
import { displayMany2oneCell, formatListDate, formatMoney } from "@/lib/formatters";
import Link from "next/link";
import {
  Title, Text, Button, Table, Loader, Alert, Group, Stack,
  ActionIcon, Modal, Pagination, TextInput, Paper, ScrollArea, Badge,
} from "@mantine/core";
import {
  IconPlus, IconAlertCircle, IconTrash, IconPencil,
  IconSearch, IconSortAscending, IconSortDescending, IconArrowsSort,
} from "@tabler/icons-react";
import { notifications } from "@mantine/notifications";
import { fetchList, deleteRecord } from "@/lib/api";

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
  /** Schema field metadata from ui-config — drives badge / monetary / many2one / date cells */
  fieldMeta?: FieldMeta[];
  createHref?: string;
  editHref?: (id: string) => string;
  pageSize?: number;
}

type SortDir = "asc" | "desc" | null;

function useEnhancedColumns(columns: Column[], fieldMeta?: FieldMeta[]): Column[] {
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
      if (m?.type === "monetary") {
        return { ...col, render: (v: unknown) => formatMoney(v) };
      }
      if (m?.type === "many2one") {
        return {
          ...col,
          render: (_v: unknown, row: Record<string, unknown>) => displayMany2oneCell(row, col.key),
        };
      }
      if (m?.type === "date" || col.key.endsWith("_date") || col.key === "create_date") {
        return { ...col, render: (v: unknown) => formatListDate(v) };
      }
      return col;
    });
  }, [columns, fieldMeta]);
}

export default function ResourceList({
  title, resource, columns, fieldMeta, createHref, editHref, pageSize = 50,
}: Props) {
  const displayColumns = useEnhancedColumns(columns, fieldMeta);
  const [items, setItems] = useState<Record<string, unknown>[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  // Search state
  const [searchInput, setSearchInput] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Sort state
  const [orderBy, setOrderBy] = useState<string | null>(null);
  const [orderDir, setOrderDir] = useState<SortDir>(null);

  // Debounced search handler
  const handleSearchChange = useCallback((value: string) => {
    setSearchInput(value);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setSearchQuery(value);
      setPage(1);
    }, 300);
  }, []);

  // Cleanup debounce timer on unmount
  useEffect(() => {
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, []);

  // Fetch data when resource, page, search, or sort changes
  useEffect(() => {
    setLoading(true);
    const params: Record<string, unknown> = {
      limit: pageSize,
      offset: (page - 1) * pageSize,
    };
    if (searchQuery) params.name__contains = searchQuery;
    if (orderBy && orderDir) {
      params.order_by = orderBy;
      params.order_dir = orderDir;
    }
    fetchList(resource, params)
      .then((d) => { setItems(d.items ?? []); setTotal(d.total ?? 0); })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [resource, page, searchQuery, orderBy, orderDir, pageSize]);

  // Client-side filtering: filter items where any column value contains search text
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

  // Column sort toggle: asc -> desc -> no sort
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

  // Sort indicator icon for a column
  function renderSortIcon(columnKey: string) {
    if (orderBy !== columnKey) {
      return <IconArrowsSort size={14} style={{ opacity: 0.3 }} />;
    }
    if (orderDir === "asc") {
      return <IconSortAscending size={14} />;
    }
    return <IconSortDescending size={14} />;
  }

  async function handleDelete() {
    if (!deleteId) return;
    setDeleting(true);
    try {
      await deleteRecord(resource, deleteId);
      setItems((prev) => prev.filter((r) => String(r.id) !== deleteId));
      setTotal((t) => t - 1);
      notifications.show({ title: "Deleted", message: "Record has been deleted.", color: "orange" });
    } catch (e: unknown) {
      notifications.show({ title: "Error", message: (e as { message: string }).message, color: "red" });
    } finally {
      setDeleting(false);
      setDeleteId(null);
    }
  }

  const totalPages = Math.ceil(total / pageSize);

  return (
    <>
      <Stack gap="md">
        <Paper>
          <Group justify="space-between" align="flex-end" mb="sm">
            <Stack gap={2}>
              <Title order={3}>{title}</Title>
              {!loading && (
                <Group gap="xs">
                  <Badge variant="light" color="blue">{total}</Badge>
                  <Text size="sm" c="dimmed">records</Text>
                </Group>
              )}
            </Stack>
            {createHref && (
              <Button component={Link} href={createHref} leftSection={<IconPlus size={16} />} size="sm">
                New
              </Button>
            )}
          </Group>

          <TextInput
            placeholder="Search records..."
            leftSection={<IconSearch size={16} />}
            value={searchInput}
            onChange={(e) => handleSearchChange(e.currentTarget.value)}
            size="sm"
            styles={{
              input: {
                background: "var(--mantine-color-body)",
                borderColor: "var(--mantine-color-default-border)",
                color: "var(--mantine-color-text)",
              },
            }}
          />
        </Paper>

        {loading && <Loader color="gray" size="sm" />}
        {error && <Alert icon={<IconAlertCircle size={16} />} color="red" title="Error">{error}</Alert>}

        {!loading && !error && (
          <>
            <Paper>
              <ScrollArea>
                <Table
                  striped
                  highlightOnHover
                  withTableBorder
                  withColumnBorders
                  styles={{
                    table: { background: "var(--mantine-color-body)", minWidth: 860 },
                    thead: { background: "var(--mantine-color-default-hover)" },
                    th: {
                      color: "var(--mantine-color-gray-7)",
                      fontWeight: 600,
                      fontSize: 12,
                      textTransform: "uppercase",
                      letterSpacing: "0.05em",
                    },
                    td: { color: "var(--mantine-color-text)" },
                  }}
                >
                  <Table.Thead>
                    <Table.Tr>
                      {displayColumns.map((c) => (
                        <Table.Th
                          key={c.key}
                          onClick={() => handleSort(c.key)}
                          style={{
                            cursor: "pointer",
                            userSelect: "none",
                            ...(orderBy === c.key
                              ? {
                                  color: "var(--mantine-color-blue-7)",
                                  background: "var(--mantine-color-blue-0)",
                                }
                              : {}),
                          }}
                        >
                          <Group gap={4} wrap="nowrap">
                            {c.label}
                            {renderSortIcon(c.key)}
                          </Group>
                        </Table.Th>
                      ))}
                      <Table.Th style={{ width: 80 }}></Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {filteredItems.length === 0 ? (
                      <Table.Tr>
                        <Table.Td colSpan={displayColumns.length + 1}>
                          <Text c="dimmed" ta="center" py="xl">No records</Text>
                        </Table.Td>
                      </Table.Tr>
                    ) : (
                      filteredItems.map((row) => (
                        <Table.Tr key={String(row.id)}>
                          {displayColumns.map((c) => (
                            <Table.Td key={c.key}>
                              {c.render ? c.render(row[c.key], row) : String(row[c.key] ?? "—")}
                            </Table.Td>
                          ))}
                          <Table.Td>
                            <Group gap={4} wrap="nowrap">
                              {editHref && (
                                <ActionIcon component={Link} href={editHref(String(row.id))} variant="light" color="gray" size="sm">
                                  <IconPencil size={14} />
                                </ActionIcon>
                              )}
                              <ActionIcon variant="light" color="red" size="sm" onClick={() => setDeleteId(String(row.id))}>
                                <IconTrash size={14} />
                              </ActionIcon>
                            </Group>
                          </Table.Td>
                        </Table.Tr>
                      ))
                    )}
                  </Table.Tbody>
                </Table>
              </ScrollArea>
            </Paper>

            {totalPages > 1 && (
              <Pagination value={page} onChange={setPage} total={totalPages} size="sm"
                styles={{ root: { justifyContent: "flex-end" } }} />
            )}
          </>
        )}
      </Stack>

      <Modal
        opened={Boolean(deleteId)} onClose={() => setDeleteId(null)}
        title="Confirm delete" size="sm"
        styles={{
          content: { background: "var(--mantine-color-body)" },
          header: { background: "var(--mantine-color-body)" },
        }}
      >
        <Stack gap="md">
          <Text size="sm" c="dimmed">Are you sure you want to delete this record? This action cannot be undone.</Text>
          <Group justify="flex-end">
            <Button variant="subtle" color="gray" onClick={() => setDeleteId(null)}>Cancel</Button>
            <Button color="red" loading={deleting} onClick={handleDelete} leftSection={<IconTrash size={16} />}>Delete</Button>
          </Group>
        </Stack>
      </Modal>
    </>
  );
}
