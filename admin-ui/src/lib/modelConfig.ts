import { fetchUiConfig, type UiConfig, type ModelConfig, type FieldMeta } from "./api";
import { getQueryClient } from "./queryClient";
import { queryKeys } from "./queryKeys";
import { parseListView, parseFormView, parseFormLayout } from "./viewParser";
import {
  isJsonView,
  parseJsonFormLayout,
  parseJsonFormView,
  parseJsonListView,
} from "./viewJson";
import type { ColumnDef } from "./viewParser";
import type { FieldDef } from "@/components/ResourceForm";

// Legacy Promise cache — prefer useUiConfig() / TanStack Query.
let _cache: Promise<UiConfig> | null = null;

export function getCachedUiConfig(): Promise<UiConfig> {
  const qc = getQueryClient();
  const cached = qc.getQueryData<UiConfig>(queryKeys.uiConfig());
  if (cached) return Promise.resolve(cached);
  if (!_cache) {
    _cache = fetchUiConfig()
      .then((data) => {
        qc.setQueryData(queryKeys.uiConfig(), data);
        return data;
      })
      .catch((err) => {
        _cache = null;
        throw err;
      });
  }
  return _cache;
}

/** Clear ui-config cache after module enable/disable. */
export function invalidateUiConfigCache(): void {
  _cache = null;
  getQueryClient().invalidateQueries({ queryKey: queryKeys.uiConfig() });
}

export function findModel(cfg: UiConfig, mod: string, model: string): ModelConfig | null {
  const modCfg = cfg.modules.find((m) => m.name === mod);
  if (!modCfg) return null;
  const key = `${mod}.${model}`;
  return modCfg.models.find((m) => m.name === key) ?? null;
}

/** Build list columns: JSON view → XML fallback → auto-generated from schema */
export function modelToColumns(m: ModelConfig): ColumnDef[] {
  if (m.views.list) {
    if (isJsonView(m.views.list)) {
      const cols = parseJsonListView(m.views.list);
      if (cols.length > 0) return cols;
    } else if (typeof m.views.list === "string") {
      const cols = parseListView(m.views.list);
      if (cols.length > 0) return cols;
    }
  }
  const skipInList = new Set(["password", "password_hash", "description", "notes", "body"]);
  return m.fields
    .filter((f) => f.type !== "textarea" && !skipInList.has(f.name))
    .map((f) => ({
      key: f.name,
      label: f.label,
      ...(f.name === "status" ? { widget: "badge" as const } : {}),
    }));
}

/** Build form fields: JSON/XML view override merged with schema metadata */
export function modelToFields(m: ModelConfig): FieldDef[] {
  const metaByName = new Map(m.fields.map((f) => [f.name, f]));
  if (m.views.form) {
    let fields: FieldDef[] = [];
    if (isJsonView(m.views.form)) {
      fields = parseJsonFormView(m.views.form);
    } else if (typeof m.views.form === "string") {
      fields = parseFormView(m.views.form);
    }
    if (fields.length > 0) {
      return fields.map((f) => enrichFieldDef(f, metaByName.get(f.key)));
    }
  }
  return m.fields.map(fieldMetaToFieldDef);
}

function fieldMetaToFieldDef(f: FieldMeta): FieldDef {
  if (f.type === "many2many") {
    return {
      key: f.name,
      label: f.label,
      type: "many2many",
      required: f.required,
      relation: f.relation,
      optionValue: f.optionValue,
      optionLabel: f.optionLabel,
    };
  }
  if (f.type === "multi_select") {
    return {
      key: f.name,
      label: f.label,
      type: "multi_select",
      required: f.required,
      optionsResource: f.optionsResource,
      optionValue: f.optionValue,
      optionLabel: f.optionLabel,
    };
  }
  if (f.type === "tags") {
    return {
      key: f.name,
      label: f.label,
      type: "tags",
      required: f.required,
      options: f.options,
      relation: f.relation,
    };
  }
  return {
    key: f.name,
    label: f.label,
    type: f.type as FieldDef["type"],
    required: f.required,
    options: f.options,
    relation: f.relation,
    currencyCode: f.currency_code,
  };
}

export interface FormPanels {
  sections?: { title?: string; fields: FieldDef[] }[];
  tabs?: { title: string; sections: { title?: string; fields: FieldDef[] }[] }[];
}

/** Form fields + optional grouped panels from JSON or XML layout. */
export function modelToFormStructure(m: ModelConfig): { fields: FieldDef[]; panels?: FormPanels } {
  const fields = modelToFields(m);
  if (!m.views.form) return { fields };

  if (isJsonView(m.views.form)) {
    const rawLayout = parseJsonFormLayout(m.views.form);
    if (!rawLayout) return { fields };
    const byKey = new Map(fields.map((f) => [f.key, f]));
    const pick = (keys: string[]) => keys.map((k) => byKey.get(k)).filter(Boolean) as FieldDef[];

    if (rawLayout.tabs?.length) {
      const tabs = rawLayout.tabs.map((t) => ({
        title: t.title,
        sections: t.sections.map((s) => ({
          title: s.title,
          fields: pick(s.fields.map((f) => f.key)),
        })).filter((s) => s.fields.length),
      }));
      const panels: FormPanels = { tabs: _appendOrphanTabs(fields, tabs) };
      return { fields, panels };
    }
    if (rawLayout.sections?.length) {
      const sections = rawLayout.sections.map((s) => ({
        title: s.title,
        fields: pick(s.fields.map((f) => f.key)),
      })).filter((s) => s.fields.length);
      const panels: FormPanels = { sections: _appendOrphanSections(fields, sections) };
      return { fields, panels };
    }
    return { fields };
  }

  if (typeof m.views.form !== "string") return { fields };
  const layout = parseFormLayout(m.views.form);
  if (!layout || layout.kind === "flat") return { fields };

  const byKey = new Map(fields.map((f) => [f.key, f]));
  const pick = (keys: string[]) => keys.map((k) => byKey.get(k)).filter(Boolean) as FieldDef[];

  if (layout.kind === "sections") {
    const sections = layout.sections.map((s) => ({
      title: s.title,
      fields: pick(s.fieldKeys),
    })).filter((s) => s.fields.length);
    const panels: FormPanels = { sections: _appendOrphanSections(fields, sections) };
    return { fields, panels };
  }

  if (layout.kind === "tabs") {
    const tabs = layout.tabs.map((t) => ({
      title: t.title,
      sections: t.sections.map((s) => ({
        title: s.title,
        fields: pick(s.fieldKeys),
      })).filter((s) => s.fields.length),
    }));
    const panels: FormPanels = { tabs: _appendOrphanTabs(fields, tabs) };
    return { fields, panels };
  }

  return { fields };
}

function _usedKeys(panels: FormPanels): Set<string> {
  const used = new Set<string>();
  panels.sections?.forEach((s) => s.fields.forEach((f) => used.add(f.key)));
  panels.tabs?.forEach((t) => t.sections.forEach((s) => s.fields.forEach((f) => used.add(f.key))));
  return used;
}

function _appendOrphanSections(all: FieldDef[], sections: { title?: string; fields: FieldDef[] }[]) {
  const used = new Set(sections.flatMap((s) => s.fields.map((f) => f.key)));
  const orphans = all.filter((f) => !used.has(f.key));
  if (orphans.length) sections.push({ title: "Other", fields: orphans });
  return sections;
}

function _appendOrphanTabs(
  all: FieldDef[],
  tabs: { title: string; sections: { title?: string; fields: FieldDef[] }[] }[],
) {
  const used = _usedKeys({ tabs });
  const orphans = all.filter((f) => !used.has(f.key));
  if (orphans.length && tabs.length) {
    tabs[tabs.length - 1].sections.push({ title: "Other", fields: orphans });
  }
  return tabs;
}

function enrichFieldDef(field: FieldDef, meta?: FieldMeta): FieldDef {
  if (!meta) return field;
  if (meta.type === "tags") {
    return { ...field, type: "tags" };
  }
  if (meta.type === "many2many") {
    return {
      ...field,
      type: "many2many",
      relation: meta.relation ?? field.relation,
      optionValue: meta.optionValue ?? field.optionValue,
      optionLabel: meta.optionLabel ?? field.optionLabel,
    };
  }
  if (meta.type === "multi_select") {
    return {
      ...field,
      type: "multi_select",
      optionsResource: meta.optionsResource ?? field.optionsResource,
      optionValue: meta.optionValue ?? field.optionValue,
      optionLabel: meta.optionLabel ?? field.optionLabel,
    };
  }
  if (meta.type === "many2one" || meta.type === "monetary") {
    return {
      ...field,
      type: meta.type,
      relation: meta.relation ?? field.relation,
      options: field.options ?? meta.options,
      currencyCode: meta.currency_code ?? field.currencyCode,
    };
  }
  if (field.type === "text" && meta.type !== "text") {
    return {
      ...field,
      type: meta.type as FieldDef["type"],
      options: meta.options ?? field.options,
      relation: meta.relation ?? field.relation,
    };
  }
  return {
    ...field,
    relation: meta.relation ?? field.relation,
    options: field.options ?? meta.options,
    optionsResource: meta.optionsResource ?? field.optionsResource,
    optionValue: meta.optionValue ?? field.optionValue,
    optionLabel: meta.optionLabel ?? field.optionLabel,
  };
}
