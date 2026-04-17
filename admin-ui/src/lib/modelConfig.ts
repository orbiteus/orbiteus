import { fetchUiConfig, type UiConfig, type ModelConfig, type FieldMeta } from "./api";
import { parseListView, parseFormView, parseFormLayout } from "./viewParser";
import type { ColumnDef } from "./viewParser";
import type { FieldDef } from "@/components/ResourceForm";

// Module-level cache — fetched once per session
let _cache: Promise<UiConfig> | null = null;

export function getCachedUiConfig(): Promise<UiConfig> {
  if (!_cache) {
    _cache = fetchUiConfig().catch((err) => {
      _cache = null; // allow retry on failure
      throw err;
    });
  }
  return _cache;
}

export function findModel(cfg: UiConfig, mod: string, model: string): ModelConfig | null {
  const modCfg = cfg.modules.find((m) => m.name === mod);
  if (!modCfg) return null;
  const key = `${mod}.${model}`;
  return modCfg.models.find((m) => m.name === key) ?? null;
}

/** Build list columns: XML view override → auto-generated from schema fields */
export function modelToColumns(m: ModelConfig): ColumnDef[] {
  if (m.views.list) {
    const cols = parseListView(m.views.list);
    if (cols.length > 0) return cols;
  }
  return m.fields
    .filter((f) => f.type !== "textarea") // skip long-text fields in list
    .map((f) => ({
      key: f.name,
      label: f.label,
      ...(f.name === "status" ? { widget: "badge" as const } : {}),
    }));
}

/** Build form fields: XML view override merged with schema metadata (many2one, monetary, …) */
export function modelToFields(m: ModelConfig): FieldDef[] {
  const metaByName = new Map(m.fields.map((f) => [f.name, f]));
  if (m.views.form) {
    const fields = parseFormView(m.views.form);
    if (fields.length > 0) {
      return fields.map((f) => enrichFieldDef(f, metaByName.get(f.key)));
    }
  }
  return m.fields.map(fieldMetaToFieldDef);
}

function fieldMetaToFieldDef(f: FieldMeta): FieldDef {
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
  };
}

export interface FormPanels {
  sections?: { title?: string; fields: FieldDef[] }[];
  tabs?: { title: string; sections: { title?: string; fields: FieldDef[] }[] }[];
}

/** Form fields + optional grouped panels from XML layout (groups / notebook). */
export function modelToFormStructure(m: ModelConfig): { fields: FieldDef[]; panels?: FormPanels } {
  const fields = modelToFields(m);
  if (!m.views.form) return { fields };
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
  if (meta.type === "many2one" || meta.type === "monetary") {
    return {
      ...field,
      type: meta.type,
      relation: meta.relation ?? field.relation,
      options: field.options ?? meta.options,
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
  };
}
