import type { MessageCatalog } from "./core";

/** One locale slice contributed by a module or deployment overlay. */
export type LanguagePack = {
  /** BCP-47-ish code, e.g. `en`, `pl`, `es`. */
  code: string;
  /** Human label for user profile / language picker. */
  label?: string;
  /** dayjs / Mantine DatesProvider locale id; defaults to `code`. */
  dayjsLocale?: string;
  /** Message key → translated string (overrides core for this code). */
  messages: MessageCatalog;
};

/** Later layers win on duplicate keys. */
export function mergeMessageCatalogs(...layers: MessageCatalog[]): MessageCatalog {
  return Object.assign({}, ...layers);
}

/** Merge per-language catalogs from core + packs + runtime overrides. */
export function mergeAllCatalogs(
  base: Record<string, MessageCatalog>,
  ...layers: Array<Partial<Record<string, MessageCatalog>>>
): Record<string, MessageCatalog> {
  const langs = new Set<string>(Object.keys(base));
  for (const layer of layers) {
    for (const code of Object.keys(layer)) {
      langs.add(code);
    }
  }
  const out: Record<string, MessageCatalog> = {};
  for (const code of langs) {
    out[code] = mergeMessageCatalogs(
      base[code] ?? {},
      ...layers.map((layer) => layer[code] ?? {}),
    );
  }
  return out;
}
