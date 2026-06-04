"use client";

import { useMemo, useState } from "react";
import { Skeleton, Stack, Text, Title, Progress, Group, Paper } from "@mantine/core";
import type { FieldMeta } from "@/lib/api";
import { humanizeFieldName, useI18n } from "@/lib/i18n";
import EmptyState from "@/components/EmptyState";
import { useResourceList } from "@/lib/queries/resources";
import { relationToResource } from "@/lib/relationPath";

interface Props {
  resource: string;
  rowField: string;
  measureField: string;
  fieldMeta?: FieldMeta[];
}

function relationForField(meta: FieldMeta[] | undefined, fieldName: string): string | null {
  const m = meta?.find((f) => f.name === fieldName);
  if (m?.type === "many2one" && m.relation) return relationToResource(m.relation);
  return null;
}

export default function ResourceGraph({ resource, rowField, measureField, fieldMeta }: Props) {
  const { t } = useI18n();
  const rel = relationForField(fieldMeta, rowField);

  const listQuery = useResourceList(resource, { limit: 200 });
  const labelQuery = useResourceList(rel ?? "", { limit: 200 }, Boolean(rel));

  const rows = listQuery.data?.items ?? [];
  const loading = (listQuery.isLoading && !listQuery.data)
    || (Boolean(rel) && labelQuery.isLoading && !labelQuery.data);

  const labels = useMemo(() => {
    const items = labelQuery.data?.items ?? [];
    const map: Record<string, string> = {};
    for (const it of items) {
      const id = String((it as Record<string, unknown>).id ?? "");
      const name = String((it as Record<string, unknown>).name ?? id);
      if (id) map[id] = name;
    }
    return map;
  }, [labelQuery.data]);

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

  if (loading) {
    return (
      <Stack gap="xs">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} height={42} radius="sm" />
        ))}
      </Stack>
    );
  }

  if (chartData.length === 0) {
    return (
      <EmptyState
        title={t("chart.noData")}
        description={t("chart.noData", { rowField: rowFieldLabel, measureField: measureFieldLabel })}
      />
    );
  }

  const maxValue = Math.max(...chartData.map((d) => d.value), 1);

  return (
    <Stack gap="md">
      <Title order={4}>{t("chart.by", { field: rowFieldLabel })}</Title>
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
