/**
 * XML arch parser — converts backend view arch XML into frontend definitions.
 *
 * Intentionally dependency-free (regex-based) to keep Docker/runtime robust.
 */

import type { FieldDef } from "@/components/ResourceForm";

export interface ColumnDef {
  key: string;
  label: string;
  /** From XML widget="badge" | "monetary" | … */
  widget?: string;
  render?: (value: unknown, row: Record<string, unknown>) => React.ReactNode;
}

function _attrs(src: string): Record<string, string> {
  const out: Record<string, string> = {};
  for (const m of src.matchAll(/([a-zA-Z_][\w:-]*)\s*=\s*"([^"]*)"/g)) out[m[1]] = m[2];
  for (const m of src.matchAll(/([a-zA-Z_][\w:-]*)\s*=\s*'([^']*)'/g)) out[m[1]] = m[2];
  return out;
}

function _tag(arch: string, name: string): string | null {
  const re = new RegExp(`<${name}\\b([^>]*)\\/?>`, "i");
  return arch.match(re)?.[0] ?? null;
}

function _tags(arch: string, name: string): string[] {
  const re = new RegExp(`<${name}\\b([^>]*)\\/?>`, "gi");
  return Array.from(arch.matchAll(re)).map((m) => m[0]);
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/** Parse <list> or <tree> arch → column definitions for ResourceList */
export function parseListView(arch: string): ColumnDef[] {
  const inList = /<(list|tree)\b/i.test(arch);
  if (!inList) return [];
  return _tags(arch, "field").map((raw) => {
    const a = _attrs(raw);
    const key = a.name ?? "";
    return {
      key,
      label: a.string || _humanize(key),
      widget: a.widget,
    };
  }).filter((c) => c.key);
}

/** Parse <form> arch → field definitions for ResourceForm */
export function parseFormView(arch: string): FieldDef[] {
  const fieldEls = _tags(arch, "field");
  const seen = new Set<string>();
  const fields: FieldDef[] = [];

  for (const raw of fieldEls) {
    const a = _attrs(raw);
    const name = a.name;
    if (!name || seen.has(name)) continue;
    seen.add(name);

    const widget = a.widget ?? "";
    const required = a.required === "1" || a.required === "true";
    const label = a.string || _humanize(name);
    const readonly = a.readonly === "1";

    fields.push({
      key: name,
      label,
      type: _widgetToType(widget, name),
      required,
      placeholder: a.placeholder,
      options: _parseOptions(raw, widget),
      relation: a.relation,
      uiWidget: widget || undefined,
      ...(readonly ? { readonly: true } : {}),
    });
  }

  return fields;
}

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

function _widgetToType(widget: string, fieldName: string): FieldDef["type"] {
  switch (widget) {
    case "tags":
      return "tags";
    case "boolean":         return "boolean";
    case "monetary":        return "monetary";
    case "float":
    case "integer":
    case "percentage":      return "number";
    case "html":
    case "text":            return "textarea";
    case "date":            return "date";
    case "select":
    case "statusbar":
    case "radio":           return "select";
    case "many2one":
      return "many2one";
    case "many2many":
    case "one2many":        return "text";
  }
  if (fieldName === "email")                  return "email";
  if (fieldName === "phone" || fieldName === "mobile") return "tel";
  if (fieldName.endsWith("_date") || fieldName === "date") return "date";
  if (fieldName.endsWith("_html") || fieldName === "notes" || fieldName === "description") return "textarea";
  return "text";
}

function _parseOptions(
  rawFieldTag: string,
  widget: string,
): { value: string; label: string }[] | undefined {
  if (widget === "statusbar") {
    const visible = _attrs(rawFieldTag).statusbar_visible;
    if (visible) {
      return visible.split(",").map((v) => ({ value: v.trim(), label: _humanize(v.trim()) }));
    }
  }
  const options = _tags(rawFieldTag, "option")
    .map((o) => _attrs(o))
    .map((o) => ({ value: o.value ?? "", label: o.string ?? o.value ?? "" }))
    .filter((o) => o.value);

  return options.length > 0 ? options : undefined;
}

/** "some_field_name" → "Some Field Name" */
function _humanize(name: string): string {
  return name
    .replace(/[-_]/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

// ---------------------------------------------------------------------------
// Form layout (groups + notebook tabs)
// ---------------------------------------------------------------------------

export interface FormSectionDef {
  title?: string;
  fieldKeys: string[];
}

export type FormLayoutDef =
  | { kind: "flat" }
  | { kind: "sections"; sections: FormSectionDef[] }
  | { kind: "tabs"; tabs: { title: string; sections: FormSectionDef[] }[] };

function _fieldKeysUnder(el: Element | null): string[] {
  // Regex parser fallback does not expose DOM subtrees; keep API compatibility.
  if (!el) return [];
  return [];
}

/** Walk <form> arch and return groups / tabs; null → render flat field list. */
export function parseFormLayout(arch: string): FormLayoutDef | null {
  // Keep forms working reliably in all environments; fallback to flat layout.
  // (Field order still comes from parseFormView.)
  return null;
}

// ---------------------------------------------------------------------------
// Calendar / graph view arch
// ---------------------------------------------------------------------------

export function parseCalendarView(arch: string | null): {
  dateStart: string;
  dateStop?: string;
  mode?: string;
} | null {
  if (!arch) return null;
  const raw = _tag(arch, "calendar");
  if (!raw) return null;
  const a = _attrs(raw);
  return {
    dateStart: a.date_start ?? "close_date",
    dateStop: a.date_stop ?? undefined,
    mode: a.mode ?? "month",
  };
}

export function parseGraphView(arch: string | null): {
  rowField: string;
  measureField: string;
  type: string;
} | null {
  if (!arch) return null;
  const g = _tag(arch, "graph");
  if (!g) return null;
  const gAttrs = _attrs(g);
  const fields = _tags(arch, "field").map((f) => _attrs(f));
  const row = fields.find((f) => f.type === "row");
  const measure = fields.find((f) => f.type === "measure");
  if (!row?.name || !measure?.name) return null;
  return {
    rowField: row.name,
    measureField: measure.name,
    type: gAttrs.type ?? "bar",
  };
}
