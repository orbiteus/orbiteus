"use client";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Stack, Title, Text, Button, Group, TextInput, Textarea, Select,
  Switch, NumberInput, Alert, Paper, Loader, Tabs, TagsInput, MultiSelect, Grid,
} from "@mantine/core";
import { IconAlertCircle, IconArrowLeft, IconDeviceFloppy, IconTrash } from "@tabler/icons-react";
import { notifications } from "@mantine/notifications";
import { api, apiErrorMessage, extractApiError } from "@/lib/api";
import { useResourceDetail } from "@/lib/queries/resources";
import {
  useCreateRecord,
  useDeleteRecord,
  useUpdateRecord,
} from "@/lib/queries/mutations";
import type { FormPanels } from "@/lib/modelConfig";
import Many2OneField from "@/components/widgets/Many2OneField";
import StatusbarField from "@/components/widgets/StatusbarField";
import { MonetaryInput } from "@/components/widgets/MonetaryField";
import { PromptInput } from "@/orbiteus-ui/ai";
import type { AIScope } from "@/orbiteus-ui/ai/types";
import { useT } from "@orbiteus/i18n";
import { useAuth } from "@/lib/auth";

export interface FieldDef {
  key: string;
  label: string;
  type:
    | "text"
    | "email"
    | "tel"
    | "number"
    | "textarea"
    | "select"
    | "boolean"
    | "date"
    | "many2one"
    | "monetary"
    | "tags"
    | "multi_select"
    | "many2many";
  required?: boolean;
  placeholder?: string;
  options?: { value: string; label: string }[];
  optionsResource?: string;
  optionLabel?: string;
  optionValue?: string;
  span?: number;
  relation?: string;
  readonly?: boolean;
  uiWidget?: string;
  currencyCode?: string;
}

interface Props {
  title: string;
  resource: string;
  recordId?: string;
  fields: FieldDef[];
  /** Optional grouped layout from XML (groups / notebook). */
  panels?: FormPanels;
  backHref: string;
  onSuccess?: (record: Record<string, unknown>) => void;
  /** When set, embeds `<PromptInput>` for module-scoped AI (framework hook). */
  aiScope?: AIScope;
}

function relationApiPath(relation: string): string {
  return relation.replace(".", "/");
}

export default function ResourceForm({
  title, resource, recordId, fields, panels, backHref, onSuccess, aiScope,
}: Props) {
  const router = useRouter();
  const t = useT();
  const { user } = useAuth();
  const isEdit = Boolean(recordId);

  const createMutation = useCreateRecord(resource);
  const updateMutation = useUpdateRecord(resource, recordId);
  const deleteMutation = useDeleteRecord(resource);
  const saveMutation = isEdit ? updateMutation : createMutation;
  const saving = saveMutation.isPending;
  const deleting = deleteMutation.isPending;

  const expandFields = useMemo(
    () => fields.filter((f) => f.type === "many2one").map((f) => f.key),
    [fields],
  );
  const recordQuery = useResourceDetail(resource, recordId, expandFields);

  const [values, setValues] = useState<Record<string, unknown>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [globalError, setGlobalError] = useState("");
  const [valuesHydrated, setValuesHydrated] = useState(!isEdit);
  const [dynamicOptions, setDynamicOptions] = useState<Record<string, { value: string; label: string }[]>>({});

  const loading = isEdit && !valuesHydrated && recordQuery.isFetching;

  useEffect(() => {
    const asyncFields = fields.filter(
      (f) => f.optionsResource || (f.type === "many2many" && f.relation),
    );
    asyncFields.forEach(async (f) => {
      try {
        const path = f.optionsResource
          ? f.optionsResource
          : relationApiPath(f.relation!);
        const { data } = await api.get(`/${path}`, {
          params: { limit: 200 },
          skipGlobalErrorToast: true,
        });
        const items: Record<string, unknown>[] = data.items ?? data ?? [];
        const valueKey = f.optionValue ?? "id";
        const labelKey = f.optionLabel ?? "name";
        const opts = items.map((item) => ({
          value: String(item[valueKey]),
          label: String(item[labelKey] ?? item[valueKey]),
        }));
        setDynamicOptions((prev) => ({ ...prev, [f.key]: opts }));
      } catch {
        // ignore
      }
    });
  }, [fields]);

  useEffect(() => {
    if (!isEdit || !recordQuery.data) return;
    const data = recordQuery.data as Record<string, unknown>;
    const flat: Record<string, unknown> = {};
    fields.forEach((f) => {
      if (f.type === "tags" || f.type === "multi_select" || f.type === "many2many") {
        flat[f.key] = Array.isArray(data[f.key]) ? data[f.key] : (data[f.key] != null ? [String(data[f.key])] : []);
      } else {
        flat[f.key] = data[f.key] ?? "";
      }
    });
    setValues(flat);
    setValuesHydrated(true);
  }, [recordId, isEdit, fields, recordQuery.data]);

  useEffect(() => {
    if (recordQuery.isError) {
      setGlobalError(apiErrorMessage(recordQuery.error, "Load failed"));
    }
  }, [recordQuery.isError, recordQuery.error]);

  function set(key: string, value: unknown) {
    setValues((v) => ({ ...v, [key]: value }));
    setErrors((e) => ({ ...e, [key]: "" }));
  }

  function validateRequired(): Record<string, string> {
    const errs: Record<string, string> = {};
    fields.forEach((f) => {
      if (!f.required) return;
      const v = values[f.key];
      if (f.type === "tags" || f.type === "multi_select" || f.type === "many2many") {
        if (!Array.isArray(v) || v.length === 0) errs[f.key] = "Required field";
        return;
      }
      if (v === undefined || v === null || v === "") errs[f.key] = "Required field";
    });
    return errs;
  }

  function renderField(f: FieldDef) {
    const val = values[f.key];
    const err = errors[f.key];
    const opts = f.options ?? dynamicOptions[f.key] ?? [];
    const ro = Boolean(f.readonly);

    if (f.uiWidget === "statusbar" && opts.length > 0) {
      return (
        <StatusbarField
          key={f.key}
          label={f.label}
          value={String(val ?? opts[0]?.value ?? "")}
          options={opts}
          onChange={(v) => set(f.key, v)}
          readOnly={ro}
        />
      );
    }

    if (f.type === "many2one" && f.relation) {
      const expanded = recordQuery.data as Record<string, unknown> | undefined;
      const nameKey = `${f.key}__name`;
      const initialLabel =
        expanded && typeof expanded[nameKey] === "string" ? expanded[nameKey] as string : undefined;
      return (
        <Many2OneField
          key={f.key}
          label={f.label}
          relation={f.relation}
          value={val != null && val !== "" ? String(val) : null}
          onChange={(v) => set(f.key, v === null || v === "" ? null : v)}
          required={f.required}
          error={err}
          readOnly={ro}
          initialLabel={initialLabel}
        />
      );
    }

    if (f.type === "tags") {
      return (
        <TagsInput
          key={f.key}
          label={f.label}
          placeholder={f.placeholder ?? f.label}
          value={Array.isArray(val) ? (val as string[]) : []}
          onChange={(v) => set(f.key, v)}
          error={err}
          readOnly={ro}
        />
      );
    }

    if (f.type === "many2many") {
      return (
        <MultiSelect
          key={f.key}
          label={f.label}
          placeholder={f.placeholder ?? "Select records…"}
          data={opts}
          value={Array.isArray(val) ? (val as string[]).map(String) : []}
          onChange={(v) => set(f.key, v)}
          error={err}
          searchable
          clearable
          disabled={ro}
        />
      );
    }

    if (f.type === "multi_select") {
      return (
        <MultiSelect
          key={f.key}
          label={f.label}
          placeholder={f.placeholder ?? "Select…"}
          data={opts}
          value={Array.isArray(val) ? (val as string[]) : []}
          onChange={(v) => set(f.key, v)}
          error={err}
          searchable
          clearable
          readOnly={ro}
          disabled={ro}
        />
      );
    }

    if (f.type === "boolean") return (
      <Switch
        key={f.key}
        label={f.label}
        checked={Boolean(val)}
        onChange={(e) => set(f.key, e.currentTarget.checked)}
        disabled={ro}
      />
    );

    if (f.type === "select") return (
      <Select
        key={f.key}
        label={f.label}
        required={f.required}
        placeholder={f.placeholder ?? `Select ${f.label.toLowerCase()}`}
        data={opts}
        value={String(val ?? "")}
        onChange={(v) => set(f.key, v)}
        error={err}
        clearable
        disabled={ro}
      />
    );

    if (f.type === "textarea") return (
      <Textarea
        key={f.key}
        label={f.label}
        required={f.required}
        placeholder={f.placeholder}
        value={String(val ?? "")}
        onChange={(e) => set(f.key, e.target.value)}
        error={err}
        rows={4}
        readOnly={ro}
      />
    );

    if (f.type === "monetary") return (
      <MonetaryInput
        key={f.key}
        label={f.label}
        required={f.required}
        placeholder={f.placeholder}
        value={val === "" || val == null ? undefined : Number(val)}
        onChange={(v) => set(f.key, v ?? 0)}
        error={err}
        currencyCode={f.currencyCode}
        disabled={ro}
      />
    );

    if (f.type === "number") return (
      <NumberInput
        key={f.key}
        label={f.label}
        required={f.required}
        placeholder={f.placeholder}
        value={val === "" || val == null ? undefined : Number(val)}
        onChange={(v) => set(f.key, v ?? 0)}
        error={err}
        disabled={ro}
      />
    );

    return (
      <TextInput
        key={f.key}
        label={f.label}
        type={f.type === "email" ? "email" : f.type === "tel" ? "tel" : f.type === "date" ? "date" : "text"}
        required={f.required}
        placeholder={f.placeholder}
        value={String(val ?? "")}
        onChange={(e) => set(f.key, e.target.value)}
        error={err}
        readOnly={ro}
      />
    );
  }

  function renderFieldsBlock(fieldList: FieldDef[]) {
    // Mantine 9's Grid is more reliable than SimpleGrid for this case —
    // the latter occasionally collapsed inputs on top of each other inside
    // a `withBorder` Paper because some children rendered shadow DOM with
    // their own positioning. Explicit `Grid.Col span` also lets full-width
    // widgets (textareas, statusbars) span both columns deterministically.
    return (
      <Grid gap="sm" align="flex-start">
        {fieldList.map((f) => {
          const fullWidth = f.type === "textarea" || f.uiWidget === "statusbar";
          return (
            <Grid.Col key={f.key} span={{ base: 12, md: fullWidth ? 12 : 6 }}>
              {renderField(f)}
            </Grid.Col>
          );
        })}
      </Grid>
    );
  }

  function renderFormBody() {
    const paperStyles = {
      root: {
        background: "var(--mantine-color-default)",
        borderColor: "var(--mantine-color-default-border)",
      },
    };

    if (panels?.tabs && panels.tabs.length > 0) {
      const defaultTab = panels.tabs[0].title;
      return (
        <Tabs defaultValue={defaultTab}>
          <Tabs.List>
            {panels.tabs.map((t) => (
              <Tabs.Tab key={t.title} value={t.title}>{t.title}</Tabs.Tab>
            ))}
          </Tabs.List>
          {panels.tabs.map((t) => (
            <Tabs.Panel key={t.title} value={t.title} pt="md">
              <Stack gap="md">
                {t.sections.map((s, si) => (
                  <Paper key={si} p="md" radius="sm" withBorder styles={{ root: paperStyles.root }}>
                    <Stack gap="sm">
                      {s.title && <Title order={5}>{s.title}</Title>}
                      {renderFieldsBlock(s.fields)}
                    </Stack>
                  </Paper>
                ))}
              </Stack>
            </Tabs.Panel>
          ))}
        </Tabs>
      );
    }

    if (panels?.sections && panels.sections.length > 0) {
      return (
        <Stack gap="md">
          {panels.sections.map((s, si) => (
            <Paper key={si} p="md" radius="sm" withBorder styles={{ root: paperStyles.root }}>
              <Stack gap="sm">
                {s.title && <Title order={5}>{s.title}</Title>}
                {renderFieldsBlock(s.fields)}
              </Stack>
            </Paper>
          ))}
        </Stack>
      );
    }

    return (
      <Paper
        p="md"
        radius="sm"
        withBorder
        styles={{
          root: {
            background: "var(--mantine-color-default)",
            borderColor: "var(--mantine-color-default-border)",
          },
        }}
      >
        {renderFieldsBlock(fields)}
      </Paper>
    );
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setGlobalError("");

    const errs = validateRequired();
    if (Object.keys(errs).length) { setErrors(errs); return; }

    const fieldByKey = new Map(fields.map((f) => [f.key, f]));
    const isNullableType = (t?: FieldDef["type"]): boolean =>
      t === "many2one" || t === "date" || t === "number" || t === "monetary" || t === "select";

    const payload = Object.fromEntries(
      Object.entries(values).map(([key, raw]) => {
        const f = fieldByKey.get(key);
        if (f?.type === "tags" || f?.type === "multi_select" || f?.type === "many2many") {
          return [key, Array.isArray(raw) ? raw : []];
        }
        if (f?.type === "text" && f.key === "password" && (raw === "" || raw == null)) {
          return [key, undefined];
        }
        if (raw === undefined) return [key, null];
        if (raw === "" && isNullableType(f?.type)) return [key, null];
        return [key, raw];
      }).filter(([, v]) => v !== undefined)
    );

    try {
      const data = await saveMutation.mutateAsync(payload);

      notifications.show({
        title: isEdit ? t("form.saved") : t("form.created"),
        message: isEdit ? t("form.saved") : t("form.created"),
        color: "green",
      });

      if (resource === "base/user" && recordId && user?.id === recordId) {
        window.dispatchEvent(new Event("orbiteus:user-preferences-updated"));
      }

      if (onSuccess) {
        onSuccess(data as Record<string, unknown>);
      } else {
        router.push(backHref);
      }
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string | { msg: string; loc: string[] }[] } } };
      const detail = e.response?.data?.detail;
      if (Array.isArray(detail)) {
        const fieldErrs: Record<string, string> = {};
        detail.forEach((d) => {
          const field = d.loc?.[d.loc.length - 1];
          if (field) fieldErrs[field] = d.msg;
        });
        setErrors(fieldErrs);
      } else {
        setGlobalError(extractApiError(err, t("form.saveFailed")));
      }
    }
  }

  async function handleDelete() {
    if (!recordId) return;
    if (!confirm("Are you sure you want to delete this record? This cannot be undone.")) return;
    try {
      await deleteMutation.mutateAsync(recordId);
      notifications.show({ title: t("form.deleted"), message: t("form.recordDeleted"), color: "orange" });
      router.push(backHref);
    } catch (err: unknown) {
      setGlobalError(extractApiError(err, t("form.deleteFailed")));
    }
  }

  if (loading) {
    return (
      <Stack gap="md">
        <Paper p="md">
          <Title order={3}>{title}</Title>
          <Loader color="gray" size="sm" mt="md" />
        </Paper>
      </Stack>
    );
  }

  return (
    <form onSubmit={handleSubmit}>
      <Stack gap="md">
        <Paper>
          <Group justify="space-between" align="center">
            <Group gap="sm">
              <Button
                variant="subtle" color="gray" size="sm"
                leftSection={<IconArrowLeft size={16} />}
                onClick={() => router.push(backHref)}
                type="button"
              >
                {t("common.back")}
              </Button>
              <Title order={3}>{title}</Title>
            </Group>
            <Group gap="sm">
              {isEdit && (
                <Button
                  variant="subtle" color="red" size="sm"
                  leftSection={<IconTrash size={16} />}
                  loading={deleting}
                  onClick={handleDelete}
                  type="button"
                >
                  {t("common.delete")}
                </Button>
              )}
              <Button
                type="submit"
                leftSection={<IconDeviceFloppy size={16} />}
                loading={saving}
              >
                {isEdit ? t("common.save") : t("common.create")}
              </Button>
            </Group>
          </Group>
          <Text size="sm" c="dimmed" mt={4}>
            {t("form.completeHint")}
          </Text>
        </Paper>

        {globalError && (
          <Alert icon={<IconAlertCircle size={16} />} color="red">{globalError}</Alert>
        )}

        {renderFormBody()}

        {aiScope ? (
          <Paper p="md" withBorder>
            <Text size="sm" fw={600} mb="xs">AI assistant</Text>
            <PromptInput scope={aiScope} placeholder="Ask about this record…" />
          </Paper>
        ) : null}
      </Stack>
    </form>
  );
}
