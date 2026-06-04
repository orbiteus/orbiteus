"use client";

import { useMemo } from "react";
import {
  useI18n,
  translateFieldLabel,
  translateModelLabel,
  translateSectionLabel,
  slugifySection,
  viewLabelKey,
} from "@orbiteus/i18n";
import type { ModelConfig } from "@/lib/api";
import {
  modelToColumns,
  modelToFormStructure,
  type FormPanels,
} from "@/lib/modelConfig";
import type { ColumnDef } from "@/lib/viewParser";
import type { FieldDef } from "@/components/ResourceForm";

function translateFields(t: ReturnType<typeof useI18n>["t"], model: string, fields: FieldDef[]): FieldDef[] {
  return fields.map((f) => ({
    ...f,
    label: translateFieldLabel(t, model, f.key, f.label),
  }));
}

function translatePanels(
  t: ReturnType<typeof useI18n>["t"],
  model: string,
  panels: FormPanels | undefined,
): FormPanels | undefined {
  if (!panels) return undefined;
  const mapSection = (s: { title?: string; fields: FieldDef[] }) => ({
    title: s.title
      ? translateSectionLabel(t, model, slugifySection(s.title), s.title)
      : s.title,
    fields: translateFields(t, model, s.fields),
  });
  if (panels.sections) {
    return { sections: panels.sections.map(mapSection) };
  }
  if (panels.tabs) {
    return {
      tabs: panels.tabs.map((tab) => ({
        title: translateSectionLabel(t, model, slugifySection(tab.title), tab.title),
        sections: tab.sections.map(mapSection),
      })),
    };
  }
  return panels;
}

export function useTranslatedFormStructure(cfg: ModelConfig | null | undefined) {
  const { t } = useI18n();
  const modelName = cfg?.name ?? "";

  return useMemo(() => {
    if (!cfg) return null;
    const raw = modelToFormStructure(cfg);
    return {
      fields: translateFields(t, modelName, raw.fields),
      panels: translatePanels(t, modelName, raw.panels),
    };
  }, [cfg, modelName, t]);
}

export function useTranslatedColumns(cfg: ModelConfig | null | undefined): ColumnDef[] {
  const { t } = useI18n();
  const modelName = cfg?.name ?? "";

  return useMemo(() => {
    if (!cfg) return [];
    return modelToColumns(cfg).map((col) => ({
      ...col,
      label: translateFieldLabel(t, modelName, col.key, col.label),
    }));
  }, [cfg, modelName, t]);
}

export function useTranslatedModelTitle(cfg: ModelConfig | null | undefined, slug: string): string {
  const { t } = useI18n();
  const modelName = cfg?.name ?? "";
  const fallback = slug.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  return translateModelLabel(t, modelName, fallback);
}

export function useTranslatedViewLabel(view: string): string {
  const { t } = useI18n();
  const key = viewLabelKey(view);
  const msg = t(key);
  return msg === key ? view.charAt(0).toUpperCase() + view.slice(1) : msg;
}
