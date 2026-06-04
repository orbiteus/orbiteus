"""Provider abstract base class."""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Literal


class ProviderError(RuntimeError):
    """Raised on provider-side failures or misconfiguration."""


@dataclass
class ChatResult:
    """Normalized provider response."""

    text: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    usage_tokens: int = 0
    finish_reason: str = "stop"
    raw: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Streaming events (DoD §8.8)
# ---------------------------------------------------------------------------
#
# Adapters yield a sequence of `ChatStreamEvent` dicts. The HTTP layer
# turns each into a Server-Sent Event:
#
#     event: text          → {"delta": "..."}              (text fragment)
#     event: tool_call     → {"id": ..., "name": ...,
#                             "arguments": {...}}          (one per call)
#     event: done          → {"usage_tokens": int,
#                             "finish_reason": "..."}      (terminator)
#
# Providers that don't natively stream still get a working `chat_stream`
# via the base-class default: it awaits `chat()` once and emits the
# whole text as a single `text` event followed by `done`.

ChatStreamEventKind = Literal["text", "tool_call", "tool_result", "done"]


@dataclass
class ChatStreamEvent:
    kind: ChatStreamEventKind
    data: dict[str, Any] = field(default_factory=dict)


class Provider(ABC):
    """Provider ABC. Concrete adapters live alongside in this package."""

    name: str = ""

    @abstractmethod
    async def ping(self, api_key: str) -> bool:
        """Cheap call confirming the credential works."""

    @abstractmethod
    async def chat(
        self,
        api_key: str,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> ChatResult:
        """Send messages, return text + optional tool calls."""

    async def chat_stream(
        self,
        api_key: str,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> AsyncIterator[ChatStreamEvent]:
        """Default fallback: emit the full reply as a single text chunk
        followed by `done`. Adapters with native streaming should
        override.
        """
        result = await self.chat(
            api_key,
            messages=messages,
            tools=tools,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        if result.text:
            yield ChatStreamEvent("text", {"delta": result.text})
        for tc in result.tool_calls:
            yield ChatStreamEvent("tool_call", tc)
        yield ChatStreamEvent(
            "done",
            {
                "usage_tokens": result.usage_tokens,
                "finish_reason": result.finish_reason,
            },
        )

    @abstractmethod
    async def embed(
        self,
        api_key: str,
        *,
        texts: list[str],
        model: str | None = None,
    ) -> list[list[float]]:
        """Return one vector per input text."""
