"use client";
/**
 * SSE hooks for `/api/realtime/subscribe` (ADR-0006, ADR-0014).
 *
 * Connections are multiplexed through `realtimeHub.ts` so many open tabs
 * share a single EventSource per browser profile.
 */
import { useEffect, useRef } from "react";
import { useAuth } from "./auth";
import { subscribeRealtimeTopic } from "./realtimeHub";
import { listTopic, resourceToModel } from "./realtimeTopics";
import type { RealtimeMessage } from "./realtimeTypes";

export type { RealtimeMessage } from "./realtimeTypes";
export { resourceToModel } from "./realtimeTopics";

/**
 * Subscribe to mutations on a specific resource list and call `onChange`
 * every time the backend publishes a `record.created/updated/deleted`
 * event for that model under the user's tenant.
 */
export function useRealtimeList(
  resource: string,
  onChange: (msg: RealtimeMessage) => void,
): void {
  const { user, hydrated } = useAuth();
  const cbRef = useRef(onChange);
  useEffect(() => {
    cbRef.current = onChange;
  }, [onChange]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (!hydrated) return;
    if (!user?.tenant_id) return;

    const model = resourceToModel(resource);
    const topic = listTopic(user.tenant_id, model);

    return subscribeRealtimeTopic(topic, (msg) => cbRef.current(msg));
  }, [resource, hydrated, user?.tenant_id]);
}

/**
 * Subscribe to many topics at once (e.g. audit log union). `onEvent`
 * fires when any subscribed topic receives a message.
 */
export function useRealtimeTopics(
  topics: string[],
  onEvent: () => void,
): void {
  const cbRef = useRef(onEvent);
  useEffect(() => {
    cbRef.current = onEvent;
  }, [onEvent]);

  const key = topics.join("\0");

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (topics.length === 0) return;

    const unsubs = topics.map((topic) =>
      subscribeRealtimeTopic(topic, () => cbRef.current()),
    );

    return () => {
      for (const off of unsubs) off();
    };
  }, [key, topics]);
}
