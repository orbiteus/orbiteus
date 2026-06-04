/** Topic helpers for `/api/realtime/subscribe` (docs/11-realtime.md). */

export function resourceToModel(resource: string): string {
  const slash = resource.indexOf("/");
  if (slash < 0) return resource;
  return `${resource.slice(0, slash)}.${resource.slice(slash + 1)}`;
}

export function listTopic(tenantId: string, model: string): string {
  return `tenant:${tenantId}:model:${model}:list`;
}

export function recordTopic(tenantId: string, model: string, recordId: string): string {
  return `tenant:${tenantId}:model:${model}:record:${recordId}`;
}

export function topicsFromRealtimeMessage(msg: {
  tenant_id?: string;
  model?: string;
  record_id?: string;
}): string[] {
  if (!msg.tenant_id || !msg.model || !msg.record_id) return [];
  return [
    listTopic(msg.tenant_id, msg.model),
    recordTopic(msg.tenant_id, msg.model, msg.record_id),
  ];
}

export function buildSubscribeUrl(topics: readonly string[]): string {
  if (topics.length === 0) return "";
  const q = topics.map((t) => `topic=${encodeURIComponent(t)}`).join("&");
  return `/api/realtime/subscribe?${q}`;
}

export function unionTopicSets(sets: Iterable<ReadonlySet<string>>): string[] {
  const out = new Set<string>();
  for (const set of sets) {
    for (const topic of set) out.add(topic);
  }
  return [...out].sort();
}

export type LeaderRecord = { tabId: string; ts: number };

export function shouldClaimLeadership(
  record: LeaderRecord | null,
  tabId: string,
  now: number,
  staleMs: number,
): boolean {
  if (!record) return true;
  if (now - record.ts > staleMs) return true;
  return record.tabId === tabId;
}
