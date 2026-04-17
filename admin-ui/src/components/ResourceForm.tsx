"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Stack, Title, Text, Button, Group, TextInput, Textarea, Select,
  Switch, NumberInput, Alert, Paper, Loader, Tabs, TagsInput, SimpleGrid,
} from "@mantine/core";
import { IconAlertCircle, IconArrowLeft, IconDeviceFloppy, IconTrash } from "@tabler/icons-react";
import { notifications } from "@mantine/notifications";
import { api } from "@/lib/api";
import type { FormPanels } from "@/lib/modelConfig";
import Many2OneField from "@/components/widgets/Many2OneField";
import StatusbarField from "@/components/widgets/StatusbarField";

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
    | "tags";
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
}

export default function ResourceForm({
  title, resource, recordId, fields, panels, backHref, onSuccess,
}: Props) {
  const router = useRouter();
  const isEdit = Boolean(recordId);

  const [values, setValues] = useState<Record<string, unknown>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [globalError, setGlobalError] = useState("");
  const [loading, setLoading] = useState(isEdit);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [dynamicOptions, setDynamicOptions] = useState<Record<string, { value: string; label: string }[]>>({});

  useEffect(() => {
    const asyncFields = fields.filter((f) => f.optionsResource);
    asyncFields.forEach(async (f) => {
      try {
        const { data } = await api.get(`/${f.optionsResource}`, { skipGlobalErrorToast: true });
        const items: Record<string, unknown>[] = data.items ?? data ?? [];
        const opts = items.map((item) => ({
          value: String(item[f.optionValue ?? "id"]),
          label: String(item[f.optionLabel ?? "name"]),
        }));
        setDynamicOptions((prev) => ({ ...prev, [f.key]: opts }));
      } catch {
        // ignore
      }
    });
  }, [fields]);

  useEffect(() => {
    if (!isEdit) return;
    api.get(`/${resource}/${recordId}`, { skipGlobalErrorToast: true })
      .then(({ data }) => {
        const flat: Record<string, unknown> = {};
        fields.forEach((f) => {
          if (f.type === "tags") {
            flat[f.key] = Array.isArray(data[f.key]) ? data[f.key] : (data[f.key] != null ? [String(data[f.key])] : []);
          } else {
            flat[f.key] = data[f.key] ?? "";
          }
        });
        setValues(flat);
      })
      .catch((e) => setGlobalError(e.response?.data?.detail ?? e.message))
      .finally(() => setLoading(false));
  }, [recordId, resource, isEdit, fields]);

  function set(key: string, value: unknown) {
    setValues((v) => ({ ...v, [key]: value }));
    setErrors((e) => ({ ...e, [key]: "" }));
  }

  function validateRequired(): Record<string, string> {
    const errs: Record<string, string> = {};
    fields.forEach((f) => {
      if (!f.required) return;
      const v = values[f.key];
      if (f.type === "tags") {
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
      <NumberInput
        key={f.key}
        label={f.label}
        required={f.required}
        placeholder={f.placeholder}
        value={val === "" || val == null ? undefined : Number(val)}
        onChange={(v) => set(f.key, v ?? 0)}
        error={err}
        decimalScale={2}
        thousandSeparator=" "
        suffix={` ${f.currencyCode ?? "PLN"}`}
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
    return (
      <SimpleGrid cols={{ base: 1, md: 2 }} spacing="sm" verticalSpacing="sm">
        {fieldList.map((f) => (
          <div key={f.key} style={{ gridColumn: f.type === "textarea" ? "span 2" : undefined }}>
            {renderField(f)}
          </div>
        ))}
      </SimpleGrid>
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

    setSaving(true);
    try {
      const { data } = isEdit
        ? await api.put(`/${resource}/${recordId}`, values, { skipGlobalErrorToast: true })
        : await api.post(`/${resource}`, values, { skipGlobalErrorToast: true });

      notifications.show({
        title: isEdit ? "Saved" : "Created",
        message: isEdit ? "Record updated." : "Record created.",
        color: "green",
      });

      if (onSuccess) {
        onSuccess(data);
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
        setGlobalError(String(detail ?? "Save failed"));
      }
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (!confirm("Are you sure you want to delete this record? This cannot be undone.")) return;
    setDeleting(true);
    try {
      await api.delete(`/${resource}/${recordId}`, { skipGlobalErrorToast: true });
      notifications.show({ title: "Deleted", message: "Record has been deleted.", color: "orange" });
      router.push(backHref);
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } };
      setGlobalError(e.response?.data?.detail ?? "Delete failed");
    } finally {
      setDeleting(false);
    }
  }

  if (loading) return <Loader color="gray" size="sm" />;

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
                Back
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
                  Delete
                </Button>
              )}
              <Button
                type="submit"
                leftSection={<IconDeviceFloppy size={16} />}
                loading={saving}
              >
                {isEdit ? "Save" : "Create"}
              </Button>
            </Group>
          </Group>
          <Text size="sm" c="dimmed" mt={4}>
            Complete the form and save changes.
          </Text>
        </Paper>

        {globalError && (
          <Alert icon={<IconAlertCircle size={16} />} color="red">{globalError}</Alert>
        )}

        {renderFormBody()}
      </Stack>
    </form>
  );
}
