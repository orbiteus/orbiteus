"use client";

import { useEffect, useMemo, useState } from "react";
import { Loader, Stack, Text, Title, Progress, Group, Paper } from "@mantine/core";
import { api } from "@/lib/api";
import type { FieldMeta } from "@/lib/api";
import { humanizeFieldName, useI18n } from "@/lib/i18n";

interface Props {
  resource: string;
  rowField: string;
  measureField: string;
  fieldMeta?: FieldMeta[];
}

/** Load labels for many2one row field (e.g. stage_id → GET crm/stage). */
function relationForField(meta: FieldMeta[] | undefined, fieldName: string): string | null {
  const m = meta?.find((f) => f.name === fieldName);
  if (m?.type === "many2one" && m.relation) return m.relation.replace(".", "/");
  return null;
}

export default function ResourceGraph({ resource, rowField, measureField, fieldMeta }: Props) {
  const { t } = useI18n();
  const [rows, setRows] = useState<Record<string, unknown>[]>([]);
  const [labels, setLabels] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);

  const rel = relationForField(fieldMeta, rowField);

  useEffect(() => {
    setLoading(true);
    const p = api.get(`/${resource}`, { params: { limit: 200 } });
    const labelP = rel
      ? api.get(`/${rel}`, { params: { limit: 200 } })
      : Promise.resolve({ data: { items: [] } });
    Promise.all([p, labelP])
      .then(([listRes, relRes]) => {
        setRows(listRes.data.items ?? listRes.data ?? []);
        const items: Record<string, unknown>[] = relRes.data.items ?? relRes.data ?? [];
        const map: Record<string, string> = {};
        for (const it of items) {
          const id = String(it.id ?? "");
          const name = String(it.name ?? it.id ?? "");
          if (id) map[id] = name;
        }
        setLabels(map);
      })
      .catch(() => setRows([]))
      .finally(() => setLoading(false));
  }, [resource, rel]);

  const chartData = useMemo(() => {
    const sums = new Map<string, number>();
    for (const r of rows) {
      const key = r[rowField] != null ? String(r[rowField]) : "";
      if (!key) continue;
      const v = Number(r[measureField] ?? 0);
      sums.set(key, (sums.get(key) ?? 0) + (Number.isFinite(v) ? v : 0));
    }
    return Array.from(sums.entries()).map(([id, value]) => ({
      category: labels[id] ?? id.slice(0, 8),
      value: Math.round(value * 100) / 100,
    }));
  }, [rows, rowField, measureField, labels]);

  const rowFieldLabel = fieldMeta?.find((f) => f.name === rowField)?.label ?? humanizeFieldName(rowField);
  const measureFieldLabel = fieldMeta?.find((f) => f.name === measureField)?.label ?? humanizeFieldName(measureField);

  if (loading) return <Loader color="gray" size="sm" />;

  if (chartData.length === 0) {
    return (
      <Text c="dimmed" size="sm">
        {t("no_chart_data", { rowField: rowFieldLabel, measureField: measureFieldLabel })}
      </Text>
    );
  }

  const maxValue = Math.max(...chartData.map((d) => d.value), 1);

  return (
    <Stack gap="md">
      <Title order={4}>{t("chart_by", { field: rowFieldLabel })}</Title>
      <Stack gap="xs">
        {chartData
          .sort((a, b) => b.value - a.value)
          .slice(0, 20)
          .map((d) => (
            <Paper key={d.category} p="xs" withBorder radius="sm">
              <Group justify="space-between" mb={6}>
                <Text size="sm" fw={500}>{d.category}</Text>
                <Text size="sm" c="dimmed">{d.value}</Text>
              </Group>
              <Progress value={(d.value / maxValue) * 100} radius="xl" size="md" />
            </Paper>
          ))}
      </Stack>
    </Stack>
  );
}
