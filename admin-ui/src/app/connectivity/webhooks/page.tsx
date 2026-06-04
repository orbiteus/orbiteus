"use client";
/**
 * Settings → Webhooks
 *
 * Manage outbound webhook subscribers (`base_webhooks`, ADR-0010 outbox).
 * Each subscriber declares:
 *   - which events to listen for (record.created / updated / deleted)
 *   - optional model scope (one of the registered tenant models, or "any")
 *   - for record.updated: optional whitelist of fields whose change fires
 *     the delivery (empty list ⇒ any field change fires)
 *   - optional inbound-auth header sent with every delivery (HMAC signing
 *     in `X-Orbiteus-Signature` is unconditional)
 *
 * Backend contract (no auto-CRUD — see `modules/base/controller/router.py`):
 *   GET    /api/base/webhooks
 *   POST   /api/base/webhooks
 *   PUT    /api/base/webhooks/{id}
 *   DELETE /api/base/webhooks/{id}
 *   POST   /api/base/webhooks/{id}/test  → synthetic delivery
 *
 * Secret + auth_header_value are write-only on the wire — `GET` only
 * exposes `has_secret` / `has_auth_header_value` flags.
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Alert, Badge, Box, Button, Checkbox, Code, CopyButton, Group, Loader,
  Modal, MultiSelect, PasswordInput, Paper, Select, Stack, Switch, Table,
  Text, TextInput, Title, Tooltip,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
  IconAlertCircle, IconCopy, IconCheck, IconPencil, IconPlayerPlay, IconPlus,
  IconRefresh, IconTrash, IconWebhook,
} from "@tabler/icons-react";
import { useT } from "@orbiteus/i18n";
import { api, extractApiError } from "@/lib/api";
import { useUiConfig } from "@/lib/queries/uiConfig";
import { formatListDate } from "@/lib/formatters";

interface WebhookRow {
  id: string;
  name: string;
  url: string;
  event_mask: string[];
  model_filter: string | null;
  field_filter: string[];
  auth_header_name: string | null;
  has_auth_header_value: boolean;
  has_secret: boolean;
  is_active: boolean;
  last_delivery_at: string | null;
  last_delivery_status: string | null;
  create_date: string | null;
  /** Only populated by POST /api/base/webhooks (one-time secret reveal). */
  secret?: string;
}

interface ModelMeta {
  name: string;          // e.g. "crm.person"
  label: string;
  fields: { name: string; label: string }[];
}

interface FormState {
  id: string | null;
  name: string;
  url: string;
  event_created: boolean;
  event_updated: boolean;
  event_deleted: boolean;
  model_filter: string;       // "" → any
  field_filter: string[];
  auth_header_name: string;
  auth_header_value: string;  // only set when operator wants to (re)set it
  is_active: boolean;
  rotate_secret: boolean;
}

const EMPTY_FORM: FormState = {
  id: null,
  name: "",
  url: "",
  event_created: true,
  event_updated: true,
  event_deleted: true,
  model_filter: "",
  field_filter: [],
  auth_header_name: "",
  auth_header_value: "",
  is_active: true,
  rotate_secret: false,
};

const ANY_MODEL = "__any__";  // sentinel value for the "all models" option

function eventBadges(mask: string[], t: (key: string) => string): React.ReactNode {
  const map: { [k: string]: { label: string; color: string } } = {
    "record.created": { label: t("webhooks.eventCreate"), color: "green" },
    "record.updated": { label: t("webhooks.eventUpdate"), color: "blue" },
    "record.deleted": { label: t("webhooks.eventDelete"), color: "red" },
  };
  return (
    <Group gap={4}>
      {mask.length === 0 ? (
        <Badge size="xs" variant="light" color="gray">{t("webhooks.allEvents")}</Badge>
      ) : mask.map((e) => (
        <Badge key={e} size="xs" variant="light" color={map[e]?.color ?? "gray"}>
          {map[e]?.label ?? e}
        </Badge>
      ))}
    </Group>
  );
}

export default function WebhooksPage() {
  const t = useT();
  const uiConfigQuery = useUiConfig();
  const [items, setItems] = useState<WebhookRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const models = useMemo(() => {
    if (!uiConfigQuery.data) return [] as ModelMeta[];
    const flat: ModelMeta[] = [];
    for (const m of uiConfigQuery.data.modules) {
      for (const model of m.models) {
        flat.push({
          name: model.name,
          label: model.label || model.name,
          fields: model.fields.map((f) => ({ name: f.name, label: f.label })),
        });
      }
    }
    flat.sort((a, b) => a.name.localeCompare(b.name));
    return flat;
  }, [uiConfigQuery.data]);

  const [formOpen, setFormOpen] = useState(false);
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [submitting, setSubmitting] = useState(false);
  const [revealedSecret, setRevealedSecret] = useState<string | null>(null);

  // Initial loads
  const refreshList = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const { data } = await api.get<{ items: WebhookRow[] }>("/base/webhooks", {
        skipGlobalErrorToast: true,
      });
      setItems(data.items ?? []);
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } };
      setError(e.response?.data?.detail ?? t("webhooks.loadFailed"));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void refreshList(); }, [refreshList]);

  // Field options for the *currently selected* model in the form. When
  // model_filter is empty (any model), we union every model's fields so
  // the user can still scope updates by a common field name like "name".
  const fieldOptions = useMemo(() => {
    if (form.model_filter) {
      const m = models.find((x) => x.name === form.model_filter);
      return (m?.fields ?? []).map((f) => ({ value: f.name, label: `${f.name} — ${f.label}` }));
    }
    const seen = new Set<string>();
    const out: { value: string; label: string }[] = [];
    for (const m of models) {
      for (const f of m.fields) {
        if (seen.has(f.name)) continue;
        seen.add(f.name);
        out.push({ value: f.name, label: f.name });
      }
    }
    out.sort((a, b) => a.value.localeCompare(b.value));
    return out;
  }, [form.model_filter, models]);

  function openCreate() {
    setForm(EMPTY_FORM);
    setRevealedSecret(null);
    setFormOpen(true);
  }

  function openEdit(row: WebhookRow) {
    setForm({
      id: row.id,
      name: row.name,
      url: row.url,
      event_created: row.event_mask.includes("record.created"),
      event_updated: row.event_mask.includes("record.updated"),
      event_deleted: row.event_mask.includes("record.deleted"),
      model_filter: row.model_filter ?? "",
      field_filter: row.field_filter ?? [],
      auth_header_name: row.auth_header_name ?? "",
      auth_header_value: "",
      is_active: row.is_active,
      rotate_secret: false,
    });
    setRevealedSecret(null);
    setFormOpen(true);
  }

  function buildEventMask(f: FormState): string[] {
    const out: string[] = [];
    if (f.event_created) out.push("record.created");
    if (f.event_updated) out.push("record.updated");
    if (f.event_deleted) out.push("record.deleted");
    return out;
  }

  async function submit() {
    setSubmitting(true);
    try {
      const event_mask = buildEventMask(form);
      const body: Record<string, unknown> = {
        name: form.name.trim(),
        url: form.url.trim(),
        event_mask,
        model_filter: form.model_filter || null,
        // Only include field_filter when "update" is in the mask, so
        // that toggling update off cleanly clears the gate.
        field_filter: form.event_updated ? form.field_filter : [],
        auth_header_name: form.auth_header_name.trim() || null,
        is_active: form.is_active,
      };
      if (form.auth_header_value.trim()) {
        body.auth_header_value = form.auth_header_value.trim();
      }

      let row: WebhookRow;
      if (form.id) {
        if (form.rotate_secret) body.secret = "";  // ignored on update; UI hint only
        const { data } = await api.put<WebhookRow>(
          `/base/webhooks/${form.id}`, body, { skipGlobalErrorToast: true });
        row = data;
        notifications.show({
          title: t("webhooks.savedTitle"),
          message: t("webhooks.updatedMessage"),
          color: "green",
          icon: <IconCheck size={16} />,
        });
      } else {
        const { data } = await api.post<WebhookRow>(
          "/base/webhooks", body, { skipGlobalErrorToast: true });
        row = data;
        if (data.secret) setRevealedSecret(data.secret);
        notifications.show({
          title: t("webhooks.registeredTitle"),
          message: t("webhooks.registeredMessage"),
          color: "green",
          icon: <IconCheck size={16} />,
        });
      }
      // If the API returned a secret on create, keep the form open so
      // the operator can copy it; otherwise close.
      if (!revealedSecret && !row.secret) setFormOpen(false);
      await refreshList();
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string | unknown } } };
      const detail = e.response?.data?.detail;
      const msg = typeof detail === "string"
        ? detail
        : t("webhooks.saveFailed");
      notifications.show({ title: t("common.error"), message: msg, color: "red" });
    } finally {
      setSubmitting(false);
    }
  }

  async function onDelete(row: WebhookRow) {
    if (!confirm(t("webhooks.deleteConfirm", { name: row.name }))) return;
    try {
      await api.delete(`/base/webhooks/${row.id}`, { skipGlobalErrorToast: true });
      notifications.show({ title: t("form.deleted"), message: row.name, color: "orange" });
      await refreshList();
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } };
      notifications.show({
        title: t("webhooks.deleteFailedTitle"),
        message: e.response?.data?.detail ?? t("webhooks.deleteFailed"),
        color: "red",
      });
    }
  }

  async function onTest(row: WebhookRow) {
    try {
      const { data } = await api.post<WebhookRow>(
        `/base/webhooks/${row.id}/test`, {}, { skipGlobalErrorToast: true });
      notifications.show({
        title: t("webhooks.testDeliveredTitle"),
        message: t("webhooks.testDeliveredMessage", { status: data.last_delivery_status ?? "—" }),
        color: "green",
        icon: <IconCheck size={16} />,
      });
      await refreshList();
    } catch (err: unknown) {
      const e = err as { response?: { status?: number; data?: { detail?: { message?: string } | string } } };
      const detail = e.response?.data?.detail;
      const msg = typeof detail === "object" && detail && "message" in detail
        ? String((detail as { message: string }).message)
        : typeof detail === "string"
          ? detail
          : t("webhooks.testFailed");
      notifications.show({ title: t("webhooks.testFailedTitle"), message: msg, color: "red" });
      await refreshList();
    }
  }

  async function onToggleActive(row: WebhookRow, next: boolean) {
    try {
      await api.put(`/base/webhooks/${row.id}`, { is_active: next }, { skipGlobalErrorToast: true });
      await refreshList();
    } catch {
      notifications.show({ title: t("common.error"), message: t("webhooks.toggleFailed"), color: "red" });
    }
  }

  // --- render ----------------------------------------------------------

  return (
    <Stack gap="md">
      <Paper>
        <Group justify="space-between" align="center">
          <Group gap="sm" align="center">
            <IconWebhook size={22} stroke={1.5} />
            <Stack gap={0}>
              <Title order={3}>{t("nav.settings.webhooks")}</Title>
              <Text size="sm" c="dimmed">
                {t("webhooks.description")}
              </Text>
            </Stack>
          </Group>
          <Group gap="xs">
            <Button
              variant="default" size="xs"
              leftSection={<IconRefresh size={14} />}
              onClick={() => void refreshList()}
              loading={loading}
            >
              {t("common.refresh")}
            </Button>
            <Button
              size="sm"
              leftSection={<IconPlus size={16} />}
              onClick={openCreate}
            >
              {t("webhooks.newWebhook")}
            </Button>
          </Group>
        </Group>
      </Paper>

      {error && (
        <Alert variant="light" color="red" icon={<IconAlertCircle size={16} />}>
          {error}
        </Alert>
      )}

      <Paper p={0}>
        <Table withColumnBorders highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th style={{ width: 70 }}>{t("webhooks.active")}</Table.Th>
              <Table.Th>{t("webhooks.name")}</Table.Th>
              <Table.Th>{t("webhooks.targetUrl")}</Table.Th>
              <Table.Th>{t("webhooks.model")}</Table.Th>
              <Table.Th>{t("webhooks.events")}</Table.Th>
              <Table.Th>{t("webhooks.watchedFields")}</Table.Th>
              <Table.Th>{t("webhooks.lastDelivery")}</Table.Th>
              <Table.Th style={{ width: 200 }}> </Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {loading && items.length === 0 ? (
              <Table.Tr>
                <Table.Td colSpan={8}>
                  <Group justify="center" py="lg"><Loader size="sm" color="gray" /></Group>
                </Table.Td>
              </Table.Tr>
            ) : items.length === 0 ? (
              <Table.Tr>
                <Table.Td colSpan={8}>
                  <Text size="sm" c="dimmed" ta="center" py="lg">
                    {t("webhooks.empty")}
                  </Text>
                </Table.Td>
              </Table.Tr>
            ) : (
              items.map((row) => (
                <Table.Tr key={row.id}>
                  <Table.Td>
                    <Switch
                      size="xs"
                      checked={row.is_active}
                      onChange={(e) => void onToggleActive(row, e.currentTarget.checked)}
                    />
                  </Table.Td>
                  <Table.Td>
                    <Text size="sm" fw={500}>{row.name}</Text>
                    {row.auth_header_name && (
                      <Text size="xs" c="dimmed">
                        {t("webhooks.authLabel")}: {row.auth_header_name}
                        {row.has_auth_header_value ? "" : ` ${t("webhooks.emptyValue")}`}
                      </Text>
                    )}
                  </Table.Td>
                  <Table.Td>
                    <Code style={{ fontSize: 11, wordBreak: "break-all" }}>{row.url}</Code>
                  </Table.Td>
                  <Table.Td>
                    {row.model_filter
                      ? <Code style={{ fontSize: 11 }}>{row.model_filter}</Code>
                      : <Badge size="xs" variant="light" color="gray">{t("webhooks.any")}</Badge>}
                  </Table.Td>
                  <Table.Td>{eventBadges(row.event_mask, t)}</Table.Td>
                  <Table.Td>
                    {row.field_filter.length === 0 ? (
                      <Text size="xs" c="dimmed">{t("webhooks.anyField")}</Text>
                    ) : (
                      <Group gap={4}>
                        {row.field_filter.map((f) => (
                          <Badge key={f} size="xs" variant="light" color="gray">{f}</Badge>
                        ))}
                      </Group>
                    )}
                  </Table.Td>
                  <Table.Td>
                    {row.last_delivery_at ? (
                      <Stack gap={2}>
                        <Text size="xs">{formatListDate(row.last_delivery_at)}</Text>
                        <Badge
                          size="xs" variant="light"
                          color={row.last_delivery_status?.startsWith("2") ? "green" : "red"}
                        >
                          {row.last_delivery_status}
                        </Badge>
                      </Stack>
                    ) : <Text size="xs" c="dimmed">—</Text>}
                  </Table.Td>
                  <Table.Td>
                    <Group gap={4} justify="flex-end">
                      <Tooltip label={t("webhooks.sendTestDelivery")}>
                        <Button
                          variant="subtle" color="gray" size="xs"
                          leftSection={<IconPlayerPlay size={14} />}
                          onClick={() => void onTest(row)}
                        >
                          {t("webhooks.test")}
                        </Button>
                      </Tooltip>
                      <Tooltip label={t("webhooks.edit")}>
                        <Button
                          variant="subtle" color="gray" size="xs"
                          leftSection={<IconPencil size={14} />}
                          onClick={() => openEdit(row)}
                        >
                          {t("webhooks.edit")}
                        </Button>
                      </Tooltip>
                      <Tooltip label={t("common.delete")}>
                        <Button
                          variant="subtle" color="red" size="xs"
                          leftSection={<IconTrash size={14} />}
                          onClick={() => void onDelete(row)}
                        >
                          {t("common.delete")}
                        </Button>
                      </Tooltip>
                    </Group>
                  </Table.Td>
                </Table.Tr>
              ))
            )}
          </Table.Tbody>
        </Table>
      </Paper>

      <Modal
        opened={formOpen}
        onClose={() => { setFormOpen(false); setRevealedSecret(null); }}
        title={form.id ? t("webhooks.editWebhook") : t("webhooks.newWebhook")}
        size="lg"
        centered
      >
        <Stack gap="md">
          {revealedSecret && (
            <Alert variant="light" color="yellow" icon={<IconAlertCircle size={16} />}>
              <Stack gap="xs">
                <Text size="sm" fw={600}>
                  {t("webhooks.saveSecretNow")}
                </Text>
                <Group gap="xs">
                  <Code style={{ flex: 1, fontSize: 11, wordBreak: "break-all" }}>
                    {revealedSecret}
                  </Code>
                  <CopyButton value={revealedSecret}>
                    {({ copied, copy }) => (
                      <Button
                        size="xs" variant="default"
                        leftSection={<IconCopy size={14} />}
                        color={copied ? "green" : "gray"}
                        onClick={copy}
                      >
                        {copied ? t("webhooks.copied") : t("webhooks.copy")}
                      </Button>
                    )}
                  </CopyButton>
                </Group>
                <Text size="xs" c="dimmed">
                  {t("webhooks.secretHintPrefix")}
                  <Code style={{ fontSize: 11 }}>X-Orbiteus-Signature</Code>.
                </Text>
              </Stack>
            </Alert>
          )}

          <TextInput
            label={t("webhooks.name")}
            description={t("webhooks.nameDescription")}
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.currentTarget.value })}
            required
          />

          <TextInput
            label={t("webhooks.targetUrl")}
            description={t("webhooks.targetUrlDescription")}
            placeholder="https://example.com/orbiteus/hook"
            value={form.url}
            onChange={(e) => setForm({ ...form, url: e.currentTarget.value })}
            required
          />

          <Box>
            <Text size="sm" fw={500} mb={4}>{t("webhooks.events")}</Text>
            <Group gap="md">
              <Checkbox
                label="record.created"
                checked={form.event_created}
                onChange={(e) => setForm({ ...form, event_created: e.currentTarget.checked })}
              />
              <Checkbox
                label="record.updated"
                checked={form.event_updated}
                onChange={(e) => setForm({ ...form, event_updated: e.currentTarget.checked })}
              />
              <Checkbox
                label="record.deleted"
                checked={form.event_deleted}
                onChange={(e) => setForm({ ...form, event_deleted: e.currentTarget.checked })}
              />
            </Group>
            <Text size="xs" c="dimmed" mt={4}>
              {t("webhooks.eventsHint")}
            </Text>
          </Box>

          <Select
            label={t("webhooks.model")}
            description={t("webhooks.modelDescription")}
            placeholder={t("webhooks.selectModel")}
            data={[
              { value: ANY_MODEL, label: t("webhooks.anyModelTenant") },
              ...models.map((m) => ({ value: m.name, label: `${m.name} — ${m.label}` })),
            ]}
            value={form.model_filter || ANY_MODEL}
            onChange={(v) => setForm({
              ...form,
              model_filter: !v || v === ANY_MODEL ? "" : v,
              // Drop previously-selected fields that no longer exist on
              // the new model — keeps the payload coherent.
              field_filter: [],
            })}
            allowDeselect={false}
            searchable
          />

          {form.event_updated && (
            <MultiSelect
              label={t("webhooks.watchedFieldsRecordUpdated")}
              description={
                form.model_filter
                  ? t("webhooks.watchedFieldsHintModel")
                  : t("webhooks.watchedFieldsHintAny")
              }
              data={fieldOptions}
              value={form.field_filter}
              onChange={(v) => setForm({ ...form, field_filter: v })}
              searchable
              clearable
            />
          )}

          <Box>
            <Text size="sm" fw={500} mb={4}>{t("webhooks.inboundAuthHeaderOptional")}</Text>
            <Group gap="sm" align="flex-end">
              <TextInput
                label={t("webhooks.headerName")}
                placeholder="Authorization"
                value={form.auth_header_name}
                onChange={(e) => setForm({ ...form, auth_header_name: e.currentTarget.value })}
                style={{ flex: 1 }}
              />
              <PasswordInput
                label={form.id ? t("webhooks.headerValueKeep") : t("webhooks.headerValue")}
                placeholder="Bearer …"
                value={form.auth_header_value}
                onChange={(e) => setForm({ ...form, auth_header_value: e.currentTarget.value })}
                style={{ flex: 2 }}
              />
            </Group>
            <Text size="xs" c="dimmed" mt={4}>
              {t("webhooks.authHintPrefix")}
              <Code style={{ fontSize: 11 }}>X-Orbiteus-Signature</Code> HMAC.
              {t("webhooks.authHintMiddle")}
              <Code style={{ fontSize: 11 }}>Authorization: Bearer …</Code>.
            </Text>
          </Box>

          <Switch
            label={t("webhooks.active")}
            description={t("webhooks.activeDescription")}
            checked={form.is_active}
            onChange={(e) => setForm({ ...form, is_active: e.currentTarget.checked })}
          />

          <Group justify="flex-end">
            <Button
              variant="subtle"
              onClick={() => { setFormOpen(false); setRevealedSecret(null); }}
            >
              {t("common.close")}
            </Button>
            <Button
              loading={submitting}
              leftSection={<IconCheck size={16} />}
              onClick={() => void submit()}
              disabled={!form.name.trim() || !form.url.trim()}
            >
              {form.id ? t("webhooks.saveChanges") : t("webhooks.registerWebhook")}
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Stack>
  );
}
