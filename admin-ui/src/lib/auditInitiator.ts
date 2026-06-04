/** Display helpers for enriched audit-log `initiator` payloads from the API. */

export interface AuditInitiator {
  kind: "user" | "ai" | "portal" | "system" | string;
  label: string;
  detail?: string | null;
  user_email?: string | null;
  user_name?: string | null;
}

export function initiatorColor(kind: string): string {
  switch (kind) {
    case "user":
      return "blue";
    case "ai":
      return "violet";
    case "portal":
      return "cyan";
    case "system":
      return "gray";
    default:
      return "gray";
  }
}

export function initiatorTooltip(
  initiator: AuditInitiator | null | undefined,
  fallback: { user_id?: string | null; request_id?: string | null },
): string {
  const lines: string[] = [];
  if (initiator?.label) lines.push(initiator.label);
  if (initiator?.detail) lines.push(initiator.detail);
  if (initiator?.user_email && !initiator.label.includes(initiator.user_email)) {
    lines.push(initiator.user_email);
  }
  if (fallback.user_id) lines.push(`user_id ${fallback.user_id}`);
  if (fallback.request_id) lines.push(`request_id ${fallback.request_id}`);
  return lines.length > 0 ? lines.join("\n") : "—";
}
