from typing import Any

from app.application.ports.llm import LLMMessage, LLMProviderPort, LLMResponse
from app.config import Settings


class OpenAIProvider(LLMProviderPort):
    def __init__(self, settings: Settings):
        self._settings = settings

    @property
    def provider_name(self) -> str:
        return "openai"

    def is_configured(self) -> bool:
        return bool(self._settings.openai_api_key)

    def complete(self, model: str, messages: list[LLMMessage], **params: Any) -> LLMResponse:
        if not self.is_configured():
            raise RuntimeError("OpenAI API key is not configured")

        from openai import OpenAI

        client = OpenAI(api_key=self._settings.openai_api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            temperature=params.get("temperature"),
            max_tokens=params.get("max_tokens"),
        )
        choice = response.choices[0].message.content or ""
        usage = {}
        if response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
        return LLMResponse(content=choice, provider=self.provider_name, model=model, usage=usage)
