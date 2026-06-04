"""Google Gemini adapter (Gemini API / AI Studio keys)."""
from __future__ import annotations

import logging
import uuid
from typing import Any

from .base import ChatResult, Provider, ProviderError

logger = logging.getLogger(__name__)


def _to_gemini_tools(tools: list[dict[str, Any]]):
    from google.genai import types

    decls = []
    for tool in tools:
        decls.append(
            types.FunctionDeclaration(
                name=tool["name"],
                description=tool.get("description") or "",
                parameters=tool.get("parameters") or {"type": "object", "properties": {}},
            )
        )
    return [types.Tool(function_declarations=decls)]


def _split_messages(
    messages: list[dict[str, Any]],
) -> tuple[str, list[Any]]:
    from google.genai import types

    system_prompt = ""
    contents: list[Any] = []
    for msg in messages:
        role = msg.get("role")
        content = msg.get("content")
        if role == "system":
            system_prompt = str(content or "")
        elif role == "user":
            contents.append(
                types.Content(
                    role="user",
                    parts=[types.Part(text=str(content or ""))],
                )
            )
        elif role == "assistant":
            contents.append(
                types.Content(
                    role="model",
                    parts=[types.Part(text=str(content or ""))],
                )
            )
    return system_prompt, contents


class GeminiProvider(Provider):
    name = "gemini"
    default_chat_model = "gemini-2.0-flash"
    default_embed_model = ""

    @staticmethod
    def _client(api_key: str):
        try:
            from google import genai
        except ImportError as exc:
            raise ProviderError("google-genai SDK not installed") from exc
        return genai.Client(api_key=api_key)

    async def ping(self, api_key: str) -> bool:
        try:
            from google.genai import types

            client = self._client(api_key)
            await client.aio.models.generate_content(
                model=self.default_chat_model,
                contents="ping",
                config=types.GenerateContentConfig(max_output_tokens=1),
            )
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning("gemini.ping_failed", extra={"error": str(exc)[:200]})
            return False

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
        try:
            from google.genai import types
        except ImportError as exc:
            raise ProviderError("google-genai SDK not installed") from exc

        client = self._client(api_key)
        system_prompt, contents = _split_messages(messages)
        config_kwargs: dict[str, Any] = {
            "max_output_tokens": max_tokens,
            "temperature": temperature,
        }
        if system_prompt:
            config_kwargs["system_instruction"] = system_prompt
        if tools:
            config_kwargs["tools"] = _to_gemini_tools(tools)
            config_kwargs["automatic_function_calling"] = (
                types.AutomaticFunctionCallingConfig(disable=True)
            )

        response = await client.aio.models.generate_content(
            model=model or self.default_chat_model,
            contents=contents or "Hello",
            config=types.GenerateContentConfig(**config_kwargs),
        )

        text_parts: list[str] = []
        tool_calls: list[dict[str, Any]] = []
        candidate = (response.candidates or [None])[0]
        if candidate and candidate.content and candidate.content.parts:
            for part in candidate.content.parts:
                if getattr(part, "text", None):
                    text_parts.append(part.text)
                fc = getattr(part, "function_call", None)
                if fc and getattr(fc, "name", None):
                    raw_args = getattr(fc, "args", None) or {}
                    if isinstance(raw_args, str):
                        import json

                        try:
                            raw_args = json.loads(raw_args)
                        except json.JSONDecodeError:
                            raw_args = {}
                    tool_calls.append(
                        {
                            "id": getattr(fc, "id", None) or str(uuid.uuid4()),
                            "name": fc.name,
                            "arguments": dict(raw_args),
                        }
                    )

        usage = getattr(response, "usage_metadata", None)
        usage_tokens = int(getattr(usage, "total_token_count", 0) or 0)
        finish = "stop"
        if candidate and getattr(candidate, "finish_reason", None):
            finish = str(candidate.finish_reason).lower()

        return ChatResult(
            text="".join(text_parts),
            tool_calls=tool_calls,
            usage_tokens=usage_tokens,
            finish_reason=finish,
            raw={"model": model or self.default_chat_model},
        )

    async def embed(
        self,
        api_key: str,
        *,
        texts: list[str],
        model: str | None = None,
    ) -> list[list[float]]:
        raise ProviderError(
            "gemini provider does not support embeddings in Orbiteus; "
            "configure OpenAI or Ollama for embed_models."
        )
