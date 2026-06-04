"use client";

import axios from "axios";
import { useCallback, useEffect, useRef, useState } from "react";

import { consumeAiChatStream } from "@/lib/aiStream";

import type { AIChatMessage, AIScope } from "./types";

interface State {
  messages: AIChatMessage[];
  loading: boolean;
  error: string | null;
  hasCredential: boolean | null;
  activeRunId: string | null;
}

export interface UseAIContextOptions {
  scope: AIScope;
  /** When set, `send()` posts to `/api/ai/runs` instead of `/api/ai/chat`. */
  agentId?: string;
  /** Stream tokens via `POST /api/ai/chat?stream=1` (scope chat only). */
  stream?: boolean;
}

/**
 * AI session hook.
 *
 * - Probes `/api/ai/credentials` once for BYOK empty state.
 * - `send(text)` posts to `/api/ai/chat` or `/api/ai/runs` (when `agentId`).
 * - Optional SSE streaming for module-scoped chat.
 */
export function useAIContext({ scope, agentId, stream = false }: UseAIContextOptions) {
  const [state, setState] = useState<State>({
    messages: [],
    loading: false,
    error: null,
    hasCredential: null,
    activeRunId: null,
  });
  const abortRef = useRef<AbortController | null>(null);
  const messagesRef = useRef<AIChatMessage[]>([]);

  useEffect(() => {
    messagesRef.current = state.messages;
  }, [state.messages]);

  useEffect(() => {
    let cancelled = false;
    axios
      .get("/api/ai/credentials")
      .then((res) => {
        if (cancelled) return;
        const items = res.data?.items ?? [];
        setState((s) => ({ ...s, hasCredential: items.length > 0 }));
      })
      .catch(() => {
        if (!cancelled) setState((s) => ({ ...s, hasCredential: false }));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const send = useCallback(
    async (text: string) => {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      const prior = messagesRef.current;
      setState((s) => ({
        ...s,
        loading: true,
        error: null,
        activeRunId: null,
        messages: [...s.messages, { role: "user", content: text }],
      }));

      try {
        if (agentId) {
          const { data } = await axios.post<{
            id: string;
            status: string;
            text?: string;
            output_text?: string;
            async?: boolean;
          }>(
            "/api/ai/runs",
            { agent_id: agentId, prompt: text, async: false },
            { signal: controller.signal },
          );
          const reply = data.text ?? data.output_text ?? "";
          setState((s) => ({
            ...s,
            loading: false,
            activeRunId: data.id ?? null,
            messages: [...prior, { role: "user", content: text }, { role: "assistant", content: reply }],
          }));
          return;
        }

        if (stream) {
          let accumulated = "";
          await consumeAiChatStream({
            body: {
              scope,
              messages: [...prior, { role: "user", content: text }],
            },
            signal: controller.signal,
            handlers: {
              onText: (_delta, full) => {
                accumulated = full;
                setState((s) => ({
                  ...s,
                  messages: [
                    ...prior,
                    { role: "user", content: text },
                    { role: "assistant", content: full },
                  ],
                }));
              },
              onDone: () => {
                setState((s) => ({
                  ...s,
                  loading: false,
                  messages: [
                    ...prior,
                    { role: "user", content: text },
                    { role: "assistant", content: accumulated },
                  ],
                }));
              },
              onError: (msg) => {
                setState((s) => ({ ...s, loading: false, error: msg }));
              },
            },
          });
          setState((s) => ({ ...s, loading: false }));
          return;
        }

        const messages: AIChatMessage[] = [...prior, { role: "user", content: text }];
        const res = await axios.post<{ text: string }>(
          "/api/ai/chat",
          { scope, messages },
          { signal: controller.signal },
        );
        setState((s) => ({
          ...s,
          loading: false,
          messages: [
            ...prior,
            { role: "user", content: text },
            { role: "assistant", content: res.data.text || "" },
          ],
        }));
      } catch (err: unknown) {
        if ((err as { name?: string }).name === "AbortError") return;
        const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data
          ?.detail;
        const msg = typeof detail === "string" ? detail : "AI request failed";
        setState((s) => ({ ...s, loading: false, error: msg }));
      }
    },
    [scope, agentId, stream],
  );

  const startAsyncRun = useCallback(
    async (text: string): Promise<string | null> => {
      if (!agentId) return null;
      setState((s) => ({
        ...s,
        loading: true,
        error: null,
        activeRunId: null,
        messages: [...s.messages, { role: "user", content: text }],
      }));
      try {
        const { data } = await axios.post<{ id: string }>("/api/ai/runs", {
          agent_id: agentId,
          prompt: text,
          async: true,
        });
        setState((s) => ({ ...s, loading: true, activeRunId: data.id }));
        return data.id;
      } catch (err: unknown) {
        const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data
          ?.detail;
        const msg = typeof detail === "string" ? detail : "Agent run failed";
        setState((s) => ({ ...s, loading: false, error: msg }));
        return null;
      }
    },
    [agentId],
  );

  const applyRunUpdate = useCallback(
    (update: {
      status?: string;
      output_text?: string | null;
      error_message?: string | null;
    }) => {
      const terminal = update.status === "completed" || update.status === "failed";
      setState((s) => {
        const next = { ...s };
        if (terminal) next.loading = false;
        if (update.status === "completed" && update.output_text) {
          const lastUser = [...s.messages].reverse().find((m) => m.role === "user");
          const base = lastUser
            ? s.messages.slice(0, s.messages.findIndex((m) => m === lastUser) + 1)
            : s.messages;
          next.messages = [...base, { role: "assistant", content: update.output_text }];
        }
        if (update.status === "failed" && update.error_message) {
          next.error = update.error_message;
        }
        return next;
      });
    },
    [],
  );

  return { ...state, send, startAsyncRun, applyRunUpdate };
}
