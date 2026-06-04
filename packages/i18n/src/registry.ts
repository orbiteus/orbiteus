import type { MessageCatalog } from "./core";
import { DEFAULT_UI_LANGUAGE } from "./core";
import { mergeAllCatalogs, type LanguagePack } from "./packs";
import { SHELL_FALLBACK_EN } from "./shell-fallbacks";

export type LocaleMeta = {
  code: string;
  label: string;
  dayjsLocale: string;
};

/** Empty SSR/test fallback — canonical catalogs come from GET /api/base/i18n/messages/{lang}. */
const EMPTY_BASE: Record<string, MessageCatalog> = {
  [DEFAULT_UI_LANGUAGE]: {},
};

const modulePacks: LanguagePack[] = [];
const localeMeta = new Map<string, LocaleMeta>();

/**
 * @deprecated Prefer module i18n JSON + API. For white-label frontend overlays only.
 */
export function registerLanguagePack(pack: LanguagePack): void {
  modulePacks.push(pack);
  if (pack.label) {
    localeMeta.set(pack.code, {
      code: pack.code,
      label: pack.label,
      dayjsLocale: pack.dayjsLocale ?? pack.code,
    });
  }
}

export function registerLocaleMeta(entries: Iterable<LocaleMeta>): void {
  for (const entry of entries) {
    localeMeta.set(entry.code, entry);
  }
}

export function getRegisteredLocaleMeta(): LocaleMeta[] {
  return [...localeMeta.values()].sort((a, b) => a.label.localeCompare(b.label));
}

export function getRegisteredLanguageCodes(): string[] {
  const codes = new Set<string>([DEFAULT_UI_LANGUAGE]);
  for (const pack of modulePacks) {
    codes.add(pack.code);
  }
  for (const meta of localeMeta.values()) {
    codes.add(meta.code);
  }
  return [...codes].sort();
}

export function resolveDayjsLocale(code: string, builtins: Record<string, string>): string {
  return localeMeta.get(code)?.dayjsLocale ?? builtins[code as keyof typeof builtins] ?? code;
}

/** API/DB wins; shell fallbacks fill missing nav / Languages page keys. */
function applyShellFallbacks(catalogs: Record<string, MessageCatalog>): Record<string, MessageCatalog> {
  const codes = new Set<string>([DEFAULT_UI_LANGUAGE, ...Object.keys(catalogs)]);
  const out: Record<string, MessageCatalog> = {};
  for (const code of codes) {
    out[code] = { ...SHELL_FALLBACK_EN, ...(catalogs[code] ?? {}) };
  }
  return out;
}

/** Build catalogs: optional legacy packs → API/DB overrides → shell gap-fill. */
export function buildRuntimeCatalogs(
  overrides?: Partial<Record<string, MessageCatalog>>,
): Record<string, MessageCatalog> {
  const packLayers = modulePacks.map((p) => ({ [p.code]: p.messages }));
  return applyShellFallbacks(mergeAllCatalogs(EMPTY_BASE, ...packLayers, overrides ?? {}));
}
