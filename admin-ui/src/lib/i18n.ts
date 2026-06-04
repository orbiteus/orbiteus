/** @deprecated Import from `@orbiteus/i18n` instead. */
export { useI18n, useT } from "@orbiteus/i18n";
import { humanizeRegistrySlugForUi } from "./formatters";

export function humanizeFieldName(field: string): string {
  const base = field.replace(/_id$/, "");
  return humanizeRegistrySlugForUi(base);
}
