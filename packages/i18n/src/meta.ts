import type { Translator } from "./core";

/** Stable key for a model field label in message catalogs. */
export function fieldLabelKey(model: string, field: string): string {
  return `field.${model}.${field}`;
}

export function sectionLabelKey(model: string, section: string): string {
  return `section.${model}.${section}`;
}

export function modelLabelKey(model: string): string {
  return `model.${model}`;
}

export function viewLabelKey(view: string): string {
  return `view.${view}`;
}

export function translateFieldLabel(
  t: Translator["t"],
  model: string,
  field: string,
  fallback: string,
): string {
  const specificKey = fieldLabelKey(model, field);
  const specific = t(specificKey);
  if (specific !== specificKey) return specific;
  const genericKey = `field.${field}`;
  const generic = t(genericKey);
  if (generic !== genericKey) return generic;
  return fallback;
}

export function translateSectionLabel(
  t: Translator["t"],
  model: string,
  sectionSlug: string,
  fallback: string,
): string {
  const key = sectionLabelKey(model, sectionSlug);
  const msg = t(key);
  return msg === key ? fallback : msg;
}

export function translateModelLabel(
  t: Translator["t"],
  model: string,
  fallback: string,
): string {
  const key = modelLabelKey(model);
  const msg = t(key);
  return msg === key ? fallback : msg;
}

export function slugifySection(title: string | undefined): string {
  return (title ?? "default")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_|_$/g, "") || "default";
}
