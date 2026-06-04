import { z } from "zod";
import type { ColumnDef } from "./viewParser";
import type { FieldDef } from "@/components/ResourceForm";

const listColumnSchema = z.object({
  key: z.string(),
  label: z.string().optional(),
  widget: z.string().optional(),
});

const formSectionSchema = z.object({
  title: z.string().optional(),
  fields: z.array(z.string()),
});

const formTabSchema = z.object({
  title: z.string(),
  sections: z.array(formSectionSchema),
});

export const jsonListViewSchema = z.object({
  model: z.string(),
  type: z.literal("list"),
  columns: z.array(listColumnSchema).min(1),
});

export const jsonFormViewSchema = z.object({
  model: z.string(),
  type: z.literal("form"),
  sections: z.array(formSectionSchema).optional(),
  tabs: z.array(formTabSchema).optional(),
});

export const jsonKanbanViewSchema = z.object({
  model: z.string(),
  type: z.literal("kanban"),
  group_by: z.string(),
  card_fields: z.array(z.string()).optional(),
});

export type JsonListView = z.infer<typeof jsonListViewSchema>;
export type JsonFormView = z.infer<typeof jsonFormViewSchema>;
export type JsonKanbanView = z.infer<typeof jsonKanbanViewSchema>;

export function isJsonView(
  view: unknown,
): view is JsonListView | JsonFormView | JsonKanbanView {
  return typeof view === "object" && view !== null && "type" in view && "model" in view;
}

export function parseJsonListView(view: unknown): ColumnDef[] {
  const parsed = jsonListViewSchema.safeParse(view);
  if (!parsed.success) return [];
  return parsed.data.columns.map((c) => ({
    key: c.key,
    label: c.label ?? c.key.replace(/_/g, " ").replace(/\b\w/g, (m) => m.toUpperCase()),
    ...(c.widget ? { widget: c.widget as ColumnDef["widget"] } : {}),
  }));
}

export function parseJsonFormView(view: unknown): FieldDef[] {
  const parsed = jsonFormViewSchema.safeParse(view);
  if (!parsed.success) return [];
  const keys: string[] = [];
  if (parsed.data.sections) {
    for (const s of parsed.data.sections) keys.push(...s.fields);
  }
  if (parsed.data.tabs) {
    for (const t of parsed.data.tabs) {
      for (const s of t.sections) keys.push(...s.fields);
    }
  }
  const seen = new Set<string>();
  return keys
    .filter((k) => {
      if (seen.has(k)) return false;
      seen.add(k);
      return true;
    })
    .map((key) => ({ key, label: key.replace(/_/g, " ").replace(/\b\w/g, (m) => m.toUpperCase()), type: "text" as const }));
}

export interface JsonFormPanels {
  sections?: { title?: string; fields: FieldDef[] }[];
  tabs?: { title: string; sections: { title?: string; fields: FieldDef[] }[] }[];
}

export function parseJsonFormLayout(view: unknown): JsonFormPanels | null {
  const parsed = jsonFormViewSchema.safeParse(view);
  if (!parsed.success) return null;
  if (parsed.data.tabs?.length) {
    return {
      tabs: parsed.data.tabs.map((t) => ({
        title: t.title,
        sections: t.sections.map((s) => ({
          title: s.title,
          fields: s.fields.map((key) => ({
            key,
            label: key.replace(/_/g, " ").replace(/\b\w/g, (m) => m.toUpperCase()),
            type: "text" as const,
          })),
        })),
      })),
    };
  }
  if (parsed.data.sections?.length) {
    return {
      sections: parsed.data.sections.map((s) => ({
        title: s.title,
        fields: s.fields.map((key) => ({
          key,
          label: key.replace(/_/g, " ").replace(/\b\w/g, (m) => m.toUpperCase()),
          type: "text" as const,
        })),
      })),
    };
  }
  return null;
}

export function parseJsonKanbanView(view: unknown): JsonKanbanView | null {
  const parsed = jsonKanbanViewSchema.safeParse(view);
  return parsed.success ? parsed.data : null;
}

/** Kanban group field from JSON view or legacy XML arch string. */
export function resolveKanbanGroupField(view: string | JsonKanbanView | null | undefined): string {
  if (!view) return "";
  if (typeof view === "object" && view.type === "kanban") {
    return view.group_by || "";
  }
  if (typeof view !== "string") return "";
  if (typeof window !== "undefined") {
    try {
      const doc = new DOMParser().parseFromString(view, "text/xml");
      const k = doc.querySelector("kanban");
      return k?.getAttribute("default_group_by") ?? k?.getAttribute("group_by") ?? "";
    } catch {
      /* fall through */
    }
  }
  return (
    view.match(/default_group_by="([^"]+)"/)?.[1]
    ?? view.match(/group_by="([^"]+)"/)?.[1]
    ?? ""
  );
}
