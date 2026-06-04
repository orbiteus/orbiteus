/** SSE consumer for `POST /api/ai/chat?stream=1` (DoD §8.8). */

export type AIStreamEventKind = "text" | "tool_call" | "tool_result" | "done" | "error";

export interface AIStreamHandlers {
  onText?: (delta: string, accumulated: string) => void;
  onToolCall?: (payload: Record<string, unknown>) => void;
  onToolResult?: (payload: Record<string, unknown>) => void;
  onDone?: (payload: Record<string, unknown>) => void;
  onError?: (message: string) => void;
}

export interface AIStreamOptions {
  url?: string;
  body: Record<string, unknown>;
  signal?: AbortSignal;
  handlers: AIStreamHandlers;
}

function parseSseBlock(raw: string): { event: string; data: string } | null {
  let evName = "message";
  let evData = "";
  for (const line of raw.split("\n")) {
    if (line.startsWith("event:")) evName = line.slice(6).trim();
    else if (line.startsWith("data:")) evData += line.slice(5).trim();
  }
  if (!evData) return null;
  return { event: evName, data: evData };
}

export async function consumeAiChatStream(options: AIStreamOptions): Promise<void> {
  const { url = "/api/ai/chat?stream=1", body, signal, handlers } = options;

  const resp = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    signal,
    body: JSON.stringify(body),
  });

  if (!resp.ok) {
    let detail = "stream error";
    try {
      const text = await resp.text();
      try {
        detail = String((JSON.parse(text) as { detail?: unknown }).detail ?? detail);
      } catch {
        detail = text || detail;
      }
    } catch {
      /* ignore */
    }
    handlers.onError?.(detail);
    throw new Error(detail);
  }

  if (!resp.body) {
    const err = "Streaming response has no body";
    handlers.onError?.(err);
    throw new Error(err);
  }

  const reader = resp.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffered = "";
  let accumulated = "";

  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffered += decoder.decode(value, { stream: true });

      let sep: number;
      while ((sep = buffered.indexOf("\n\n")) !== -1) {
        const block = buffered.slice(0, sep);
        buffered = buffered.slice(sep + 2);
        const parsed = parseSseBlock(block);
        if (!parsed) continue;

        let payload: Record<string, unknown> = {};
        try {
          payload = JSON.parse(parsed.data) as Record<string, unknown>;
        } catch {
          continue;
        }

        if (parsed.event === "text") {
          const delta = String(payload.delta ?? "");
          accumulated += delta;
          handlers.onText?.(delta, accumulated);
        } else if (parsed.event === "tool_call") {
          handlers.onToolCall?.(payload);
        } else if (parsed.event === "tool_result") {
          handlers.onToolResult?.(payload);
        } else if (parsed.event === "done") {
          handlers.onDone?.(payload);
        } else if (parsed.event === "error") {
          const msg = String(payload.detail ?? "stream error");
          handlers.onError?.(msg);
          throw new Error(msg);
        }
      }
    }
  } finally {
    try {
      reader.releaseLock();
    } catch {
      /* noop */
    }
  }
}
