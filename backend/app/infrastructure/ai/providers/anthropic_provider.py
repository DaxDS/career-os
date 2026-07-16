from typing import Any

from app.application.ports.llm import LLMMessage, LLMProviderPort, LLMResponse
from app.config import Settings


class AnthropicProvider(LLMProviderPort):
    def __init__(self, settings: Settings):
        self._settings = settings

    @property
    def provider_name(self) -> str:
        return "anthropic"

    def is_configured(self) -> bool:
        return bool(self._settings.anthropic_api_key)

    def complete(self, model: str, messages: list[LLMMessage], **params: Any) -> LLMResponse:
        if not self.is_configured():
            raise RuntimeError("Anthropic API key is not configured")

        from anthropic import Anthropic

        client = Anthropic(api_key=self._settings.anthropic_api_key)
        system_parts = [m.content for m in messages if m.role == "system"]
        user_messages = [
            {"role": m.role, "content": m.content} for m in messages if m.role != "system"
        ]
        response = client.messages.create(
            model=model,
            max_tokens=params.get("max_tokens", 2048),
            temperature=params.get("temperature", 0.0),
            system="\n\n".join(system_parts) if system_parts else None,
            messages=user_messages,
        )
        content = "".join(
            block.text for block in response.content if getattr(block, "text", None)
        )
        usage = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }
        return LLMResponse(content=content, provider=self.provider_name, model=model, usage=usage)
