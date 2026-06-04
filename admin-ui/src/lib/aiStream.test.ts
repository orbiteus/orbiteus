/** Vitest for SSE chat stream parser helpers. */
import { describe, expect, it, vi } from "vitest";

import { consumeAiChatStream } from "./aiStream";

describe("consumeAiChatStream", () => {
  it("accumulates text deltas from SSE body", async () => {
    const encoder = new TextEncoder();
    const chunks = [
      'event: text\ndata: {"delta":"Hel"}\n\n',
      'event: text\ndata: {"delta":"lo"}\n\n',
      'event: done\ndata: {"usage_tokens":3,"finish_reason":"stop"}\n\n',
    ];
    let i = 0;
    const body = new ReadableStream<Uint8Array>({
      pull(controller) {
        if (i < chunks.length) {
          controller.enqueue(encoder.encode(chunks[i]));
          i += 1;
        } else {
          controller.close();
        }
      },
    });

    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        body,
      }),
    );

    const texts: string[] = [];
    await consumeAiChatStream({
      body: { scope: "global", messages: [] },
      handlers: {
        onText: (_d, acc) => texts.push(acc),
      },
    });

    expect(texts[texts.length - 1]).toBe("Hello");
    vi.unstubAllGlobals();
  });
});
