"""Anthropic provider implementation."""

from typing import Optional
from anthropic import AsyncAnthropic, AnthropicError

from .base import (
    BaseProvider,
    ProviderConfig,
    GenerationRequest,
    GenerationResponse,
    ProviderError,
    AuthenticationError,
)


class AnthropicProvider(BaseProvider):
    """Provider for Anthropic models (Claude)."""

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.client = AsyncAnthropic(
            api_key=config.api_key,
            base_url=config.base_url,
            timeout=config.timeout,
            max_retries=config.max_retries,
        )

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        """Generate text using Anthropic API."""
        try:
            params = {
                "model": self.config.model,
                "messages": [{"role": "user", "content": request.prompt}],
                "temperature": request.temperature or self.config.temperature,
                "max_tokens": request.max_tokens or self.config.max_tokens or 4096,
            }

            if request.system:
                params["system"] = request.system

            if request.stop_sequences:
                params["stop_sequences"] = request.stop_sequences

            response = await self.client.messages.create(**params)

            return GenerationResponse(
                text=response.content[0].text,
                model=response.model,
                usage={
                    "prompt_tokens": response.usage.input_tokens,
                    "completion_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
                },
                finish_reason=response.stop_reason,
                raw_response=response,
            )

        except AnthropicError as e:
            if "authentication" in str(e).lower():
                raise AuthenticationError(str(e), "anthropic", e)
            else:
                raise ProviderError(str(e), "anthropic", e)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """
        Anthropic doesn't provide embeddings directly.
        This would need to use Voyage AI or another embedding service.
        """
        raise NotImplementedError(
            "Anthropic provider doesn't support embeddings. "
            "Use OpenAI provider for embeddings."
        )

    def token_count(self, text: str) -> int:
        """
        Approximate token count for Claude.
        Claude uses a similar tokenizer to GPT, ~4 chars per token.
        """
        return len(text) // 4

    async def healthcheck(self) -> bool:
        """Check Anthropic API health."""
        try:
            # Simple test message
            await self.client.messages.create(
                model=self.config.model,
                max_tokens=10,
                messages=[{"role": "user", "content": "test"}]
            )
            return True
        except Exception:
            return False
