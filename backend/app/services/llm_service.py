import os
import anthropic
import openai


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

    def complete(self, messages: list[dict], stream: bool = False) -> str:
        if stream:
            raise NotImplementedError("Streaming not yet implemented — use chat route SSE handler")
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
