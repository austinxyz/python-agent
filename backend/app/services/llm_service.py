import os
from typing import Iterator

import anthropic
import openai


# Friendly model aliases used by the chat API → actual provider model IDs.
# Anthropic uses Claude IDs; OpenAI uses GPT IDs. The chat route accepts
# `model: "haiku" | "sonnet"` and translates via this map.
MODEL_ALIASES = {
    "anthropic": {
        "haiku": "claude-haiku-4-5-20251001",
        "sonnet": "claude-sonnet-4-6",
    },
    "openai": {
        "haiku": "gpt-4o-mini",  # fast/cheap stand-in
        "sonnet": "gpt-4o",
    },
}


class LlmService:
    def __init__(self) -> None:
        self._provider = os.environ.get("LLM_PROVIDER", "anthropic")
        self._model = os.environ.get("LLM_MODEL", "claude-haiku-4-5-20251001")
        if self._provider == "anthropic":
            self._client = anthropic.Anthropic(
                api_key=os.environ.get("ANTHROPIC_API_KEY")
            )
        else:
            self._client = openai.OpenAI(
                api_key=os.environ.get("OPENAI_API_KEY")
            )

    @property
    def provider(self) -> str:
        return self._provider

    def _resolve_model(self, alias_or_id: str | None) -> str:
        if not alias_or_id:
            return self._model
        # If caller passed a friendly alias, map to the provider's model ID
        mapping = MODEL_ALIASES.get(self._provider, {})
        return mapping.get(alias_or_id, alias_or_id)

    def complete(self, messages: list[dict], stream: bool = False) -> str:
        if stream:
            raise NotImplementedError("Use stream_complete() for SSE")
        if self._provider == "anthropic":
            response = self._client.messages.create(
                model=self._model,
                max_tokens=4096,
                messages=messages,
            )
            return response.content[0].text
        else:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
            )
            return response.choices[0].message.content

    def stream_complete(
        self,
        messages: list[dict],
        *,
        system: str | None = None,
        model: str | None = None,
        max_tokens: int = 4096,
    ) -> Iterator[str]:
        """Yield response text fragments as the LLM generates them.

        `messages` SHOULD use the OpenAI/Anthropic chat shape:
            [{"role": "user"|"assistant", "content": "..."}, ...]
        For Anthropic, an optional `system` prompt is passed separately
        (Anthropic doesn't accept role=system inside `messages`). For
        OpenAI, a system message is prepended automatically when given.
        """
        resolved = self._resolve_model(model)
        if self._provider == "anthropic":
            kwargs: dict = {
                "model": resolved,
                "max_tokens": max_tokens,
                "messages": messages,
            }
            if system:
                kwargs["system"] = system
            with self._client.messages.stream(**kwargs) as stream:
                for text in stream.text_stream:
                    if text:
                        yield text
        else:
            payload = list(messages)
            if system:
                payload = [{"role": "system", "content": system}] + payload
            response = self._client.chat.completions.create(
                model=resolved,
                messages=payload,
                stream=True,
            )
            for chunk in response:
                delta = chunk.choices[0].delta.content if chunk.choices else None
                if delta:
                    yield delta
