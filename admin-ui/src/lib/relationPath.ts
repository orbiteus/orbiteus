/** Convert dotted model name from ui-config (e.g. crm.customer) to REST path segment (crm/customer). */
export function relationToResource(relation: string): string {
  const parts = relation.split(".");
  if (parts.length < 2) return relation;
  const [mod, ...rest] = parts;
  return `${mod}/${rest.join("/")}`;
}
