"use client";
/**
 * Technical → Audit log
 *
 * Read-only viewer over the mandatory audit trail (`base_audit_log`,
 * ADR-0014). Streams the latest mutations on the tenant via the same
 * SSE backplane that drives ResourceList, so a busy system shows new
 * rows in real time without manual refresh.
 *
 * Backend contract: `GET /api/base/audit-log`
 *   query: model, record_id, actor, operation, user_id, limit, offset
 *   returns: { items: AuditRow[], total, limit, offset }
 *
 * One row covers one CRUD or auth event:
 *   id, create_date, tenant_id, actor (user|ai|portal|system),
 *   user_id, request_id, model, record_id,
 *   operation (create|update|delete|tool_call|login|login_failed),
 *   diff (Record<field, [old, new]> | null),
 *   metadata (Record<string, unknown> | null),
 *   initiator ({ kind, label, detail?, user_email?, user_name? })
 */
import { Fragment, useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Alert, Badge, Button, Code, Group, Loader, Pagination, Paper,
  Select, Stack, Table, Text, TextInput, Title, Tooltip,
} from "@mantine/core";
import {
  IconAlertCircle, IconChevronDown, IconChevronRight, IconHistory,
  IconRefresh,
} from "@tabler/icons-react";
import { useT } from "@orbiteus/i18n";
import { api, extractApiError } from "@/lib/api";
import { initiatorColor, initiatorTooltip, type AuditInitiator } from "@/lib/auditInitiator";
import { useAuth } from "@/lib/auth";
import { formatListDate } from "@/lib/formatters";
import { useUiConfig } from "@/lib/queries/uiConfig";
import { useRealtimeTopics } from "@/lib/realtime";
import { listTopic } from "@/lib/realtimeTopics";

interface AuditRow {
  id: string;
  create_date: string | null;
  tenant_id: string | null;
  actor: "user" | "ai" | "system" | string;
  user_id: string | null;
  request_id: string | null;
  model: string | null;
  record_id: string | null;
  operation: string;
  diff: Record<string, [unknown, unknown]> | null;
  metadata: Record<string, unknown> | null;
  initiator?: AuditInitiator | null;
}

interface AuditPage {
  items: AuditRow[];
  total: number;
  limit: number;
  offset: number;
}

const PAGE_SIZE = 50;

function operationColor(op: string): string {
  switch (op) {
    case "create":       return "green";
    case "update":       return "blue";
    case "delete":       return "red";
    case "tool_call":    return "violet";
    case "login":        return "gray";
    case "login_failed": return "orange";
    default:             return "gray";
  }
}

function actorColor(actor: string): string {
  return initiatorColor(actor);
}

function shortUuid(s: string | null): string {
  return s ? `${s.slice(0, 8)}…` : "—";
}

export default function AuditLogPage() {
  const t = useT();
  const operationLabel = (op: string) => {
    const labels: Record<string, string> = {
      create: t("auditLog.operation.create"),
      update: t("auditLog.operation.update"),
      delete: t("auditLog.operation.delete"),
      tool_call: t("auditLog.operation.toolCall"),
      login: t("auditLog.operation.login"),
      login_failed: t("auditLog.operation.loginFailed"),
    };
    return labels[op] ?? op;
  };
  const actorLabel = (actorName: string) => {
    const labels: Record<string, string> = {
      user: t("auditLog.actor.user"),
      ai: t("auditLog.actor.ai"),
      portal: t("auditLog.actor.portal"),
      system: t("auditLog.actor.system"),
    };
    return labels[actorName] ?? actorName;
  };
  const operationOptions = [
    { value: "", label: t("auditLog.allOperations") },
    { value: "create", label: operationLabel("create") },
    { value: "update", label: operationLabel("update") },
    { value: "delete", label: operationLabel("delete") },
    { value: "tool_call", label: operationLabel("tool_call") },
    { value: "login", label: operationLabel("login") },
    { value: "login_failed", label: operationLabel("login_failed") },
  ];
  const actorOptions = [
    { value: "", label: t("auditLog.allActors") },
    { value: "user", label: actorLabel("user") },
    { value: "ai", label: actorLabel("ai") },
    { value: "portal", label: actorLabel("portal") },
    { value: "system", label: actorLabel("system") },
  ];
  const { user } = useAuth();
  const uiConfigQuery = useUiConfig();
  const [items, setItems] = useState<AuditRow[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [page, setPage] = useState(1);
  const [model, setModel] = useState("");
  const [actor, setActor] = useState("");
  const [operation, setOperation] = useState("");

  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  const refresh = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const params: Record<string, string | number> = {
        limit: PAGE_SIZE,
        offset: (page - 1) * PAGE_SIZE,
      };
      if (model.trim()) params.model = model.trim();
      if (actor) params.actor = actor;
      if (operation) params.operation = operation;

      const { data } = await api.get<AuditPage>("/base/audit-log", {
        params,
        skipGlobalErrorToast: true,
      });
      setItems(data.items ?? []);
      setTotal(data.total ?? 0);
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } };
      setError(e.response?.data?.detail ?? t("auditLog.loadFailed"));
    } finally {
      setLoading(false);
    }
  }, [page, model, actor, operation]);

  useEffect(() => { void refresh(); }, [refresh]);

  const realtimeTopics = useMemo(() => {
    if (!user?.tenant_id || !uiConfigQuery.data) return [];
    return uiConfigQuery.data.modules.flatMap((m) =>
      m.models.map((mod) => listTopic(user.tenant_id!, mod.name)),
    );
  }, [user?.tenant_id, uiConfigQuery.data]);

  const refreshTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const onRealtimeEvent = useCallback(() => {
    if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current);
    refreshTimerRef.current = setTimeout(() => {
      void refresh();
    }, 600);
  }, [refresh]);

  useRealtimeTopics(realtimeTopics, onRealtimeEvent);

  useEffect(() => () => {
    if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current);
  }, []);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  function toggleExpanded(id: string) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function renderDiff(row: AuditRow) {
    if (!row.diff || Object.keys(row.diff).length === 0) {
      return (
        <Text size="xs" c="dimmed">
          {row.operation === "create"
            ? t("auditLog.initialValues")
            : t("auditLog.noDiff")}
        </Text>
      );
    }
    return (
      <Stack gap={4}>
        {Object.entries(row.diff).map(([field, pair]) => {
          const [oldVal, newVal] = Array.isArray(pair) ? pair : [null, pair];
          return (
            <Group key={field} gap="xs" wrap="nowrap" align="flex-start">
              <Badge variant="light" color="gray" size="xs">{field}</Badge>
              <Code style={{ fontSize: 11 }} c="red">
                {oldVal === null ? "∅" : JSON.stringify(oldVal)}
              </Code>
              <Text size="xs" c="dimmed">→</Text>
              <Code style={{ fontSize: 11 }} c="green">
                {newVal === null ? "∅" : JSON.stringify(newVal)}
              </Code>
            </Group>
          );
        })}
      </Stack>
    );
  }

  return (
    <Stack gap="md">
      <Paper>
        <Group gap="sm" align="center" justify="space-between">
          <Group gap="sm" align="center">
            <IconHistory size={22} stroke={1.5} />
            <Stack gap={0}>
              <Title order={3}>{t("nav.technical.audit")}</Title>
              <Text size="sm" c="dimmed">
                {t("auditLog.description")}
              </Text>
            </Stack>
          </Group>
          <Group gap="xs">
            <Badge variant="light" color="dark" size="lg">{total}</Badge>
            <Text size="sm" c="dimmed">{t("auditLog.events")}</Text>
            <Tooltip label={t("auditLog.refreshNow")}>
              <Button
                variant="default" size="xs"
                leftSection={<IconRefresh size={14} />}
                onClick={() => void refresh()}
                loading={loading}
              >
                {t("common.refresh")}
              </Button>
            </Tooltip>
          </Group>
        </Group>
      </Paper>

      <Paper>
        <Group gap="sm" align="flex-end">
          <TextInput
            label={t("auditLog.model")}
            placeholder={t("auditLog.modelPlaceholder")}
            value={model}
            onChange={(e) => { setModel(e.currentTarget.value); setPage(1); }}
            style={{ flex: 1, minWidth: 180 }}
          />
          <Select
            label={t("auditLog.actor")}
            data={actorOptions}
            value={actor}
            onChange={(v) => { setActor(v ?? ""); setPage(1); }}
            allowDeselect={false}
            style={{ width: 160 }}
          />
          <Select
            label={t("auditLog.operation")}
            data={operationOptions}
            value={operation}
            onChange={(v) => { setOperation(v ?? ""); setPage(1); }}
            allowDeselect={false}
            style={{ width: 180 }}
          />
        </Group>
      </Paper>

      {error && (
        <Alert variant="light" color="red" icon={<IconAlertCircle size={16} />}>
          {error}
        </Alert>
      )}

      <Paper p={0}>
        <Table withColumnBorders highlightOnHover style={{ tableLayout: "fixed" }}>
          <Table.Thead>
            <Table.Tr>
              <Table.Th style={{ width: 28 }}> </Table.Th>
              <Table.Th style={{ width: 170 }}>{t("auditLog.timestamp")}</Table.Th>
              <Table.Th style={{ width: 90 }}>{t("auditLog.actor")}</Table.Th>
              <Table.Th style={{ width: 130 }}>{t("auditLog.operation")}</Table.Th>
              <Table.Th>{t("auditLog.model")}</Table.Th>
              <Table.Th style={{ width: 110 }}>{t("auditLog.record")}</Table.Th>
              <Table.Th style={{ minWidth: 200 }}>{t("auditLog.initiator")}</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {loading && items.length === 0 ? (
              <Table.Tr>
                <Table.Td colSpan={7}>
                  <Group justify="center" py="lg"><Loader size="sm" color="gray" /></Group>
                </Table.Td>
              </Table.Tr>
            ) : items.length === 0 ? (
              <Table.Tr>
                <Table.Td colSpan={7}>
                  <Text size="sm" c="dimmed" ta="center" py="lg">
                    {t("auditLog.noEntries")}
                  </Text>
                </Table.Td>
              </Table.Tr>
            ) : (
              items.map((row) => {
                const isOpen = expanded.has(row.id);
                return (
                  <Fragment key={row.id}>
                    <Table.Tr
                      onClick={() => toggleExpanded(row.id)}
                      style={{ cursor: "pointer" }}
                    >
                      <Table.Td>
                        {isOpen ? <IconChevronDown size={14} /> : <IconChevronRight size={14} />}
                      </Table.Td>
                      <Table.Td>
                        <Text size="xs">{formatListDate(row.create_date) || "—"}</Text>
                      </Table.Td>
                      <Table.Td>
                        <Badge size="xs" variant="light" color={actorColor(row.actor)}>
                          {actorLabel(row.actor)}
                        </Badge>
                      </Table.Td>
                      <Table.Td>
                        <Badge size="xs" variant="light" color={operationColor(row.operation)}>
                          {operationLabel(row.operation)}
                        </Badge>
                      </Table.Td>
                      <Table.Td>
                        <Code style={{ fontSize: 11 }}>{row.model ?? "—"}</Code>
                      </Table.Td>
                      <Table.Td>
                        <Tooltip label={row.record_id ?? "—"} disabled={!row.record_id}>
                          <Code style={{ fontSize: 11 }}>{shortUuid(row.record_id)}</Code>
                        </Tooltip>
                      </Table.Td>
                      <Table.Td>
                        {(() => {
                          const kind = row.initiator?.kind ?? row.actor;
                          const label = row.initiator?.label
                            ?? (row.user_id ? shortUuid(row.user_id) : row.actor);
                          const tip = initiatorTooltip(row.initiator, {
                            user_id: row.user_id,
                            request_id: row.request_id,
                          });
                          return (
                            <Tooltip label={tip} multiline w={320}>
                              <Stack gap={2}>
                                <Badge size="xs" variant="light" color={initiatorColor(kind)}>
                                  {actorLabel(kind)}
                                </Badge>
                                <Text size="xs" lineClamp={2}>{label}</Text>
                              </Stack>
                            </Tooltip>
                          );
                        })()}
                      </Table.Td>
                    </Table.Tr>
                    <Table.Tr>
                      <Table.Td colSpan={7} p={0} style={{ border: 0 }}>
                        {isOpen ? (
                          <Paper m="xs" p="sm" radius="sm" withBorder
                            bg="var(--mantine-color-default)">
                            <Stack gap="xs">
                              <Group gap="xs">
                                <Badge size="xs" variant="light" color="gray">{t("auditLog.id")}</Badge>
                                <Code style={{ fontSize: 11 }}>{row.id}</Code>
                              </Group>
                              <Group gap="xs" align="flex-start">
                                <Badge size="xs" variant="light" color="gray">{t("auditLog.diff")}</Badge>
                                <div style={{ flex: 1 }}>{renderDiff(row)}</div>
                              </Group>
                              {row.initiator && (
                                <Group gap="xs" align="flex-start">
                                  <Badge size="xs" variant="light" color="gray">{t("auditLog.initiator")}</Badge>
                                  <Stack gap={2}>
                                    <Text size="xs">{row.initiator.label}</Text>
                                    {row.initiator.detail ? (
                                      <Text size="xs" c="dimmed">{row.initiator.detail}</Text>
                                    ) : null}
                                  </Stack>
                                </Group>
                              )}
                              {row.metadata && Object.keys(row.metadata).length > 0 && (
                                <Group gap="xs" align="flex-start">
                                  <Badge size="xs" variant="light" color="gray">{t("auditLog.metadata")}</Badge>
                                  <Code block style={{ flex: 1, fontSize: 11 }}>
                                    {JSON.stringify(row.metadata, null, 2)}
                                  </Code>
                                </Group>
                              )}
                            </Stack>
                          </Paper>
                        ) : null}
                      </Table.Td>
                    </Table.Tr>
                  </Fragment>
                );
              })
            )}
          </Table.Tbody>
        </Table>
      </Paper>

      {totalPages > 1 && (
        <Group justify="center">
          <Pagination
            total={totalPages}
            value={page}
            onChange={setPage}
            siblings={1}
            boundaries={1}
          />
        </Group>
      )}
    </Stack>
  );
}
