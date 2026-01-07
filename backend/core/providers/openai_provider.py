"""OpenAI provider implementation."""

import asyncio
from typing import Optional
import tiktoken
from openai import AsyncOpenAI, OpenAIError, RateLimitError as OpenAIRateLimitError

from .base import (
    BaseProvider,
    ProviderConfig,
    GenerationRequest,
    GenerationResponse,
    ProviderError,
    RateLimitError,
    AuthenticationError,
    InvalidRequestError,
)


class OpenAIProvider(BaseProvider):
    """Provider for OpenAI models (GPT-4, GPT-3.5, etc.)."""

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.client = AsyncOpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
            timeout=config.timeout,
            max_retries=config.max_retries,
        )
        self._tokenizer = None

    def _get_tokenizer(self):
        """Lazy load tokenizer."""
        if self._tokenizer is None:
            try:
                self._tokenizer = tiktoken.encoding_for_model(self.config.model)
            except KeyError:
                # Fallback to cl100k_base for unknown models
                self._tokenizer = tiktoken.get_encoding("cl100k_base")
        return self._tokenizer

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        """Generate text using OpenAI API."""
        try:
            messages = []
            if request.system:
                messages.append({"role": "system", "content": request.system})
            messages.append({"role": "user", "content": request.prompt})

            params = {
                "model": self.config.model,
                "messages": messages,
                "temperature": request.temperature or self.config.temperature,
            }

            if request.max_tokens:
                params["max_tokens"] = request.max_tokens
            elif self.config.max_tokens:
                params["max_tokens"] = self.config.max_tokens

            if request.stop_sequences:
                params["stop"] = request.stop_sequences

            if request.json_schema:
                params["response_format"] = {"type": "json_object"}

            response = await self.client.chat.completions.create(**params)

            return GenerationResponse(
                text=response.choices[0].message.content,
                model=response.model,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                },
                finish_reason=response.choices[0].finish_reason,
                raw_response=response,
            )

        except OpenAIRateLimitError as e:
            raise RateLimitError(str(e), "openai", e)
        except OpenAIError as e:
            if "authentication" in str(e).lower():
                raise AuthenticationError(str(e), "openai", e)
            elif "invalid" in str(e).lower():
                raise InvalidRequestError(str(e), "openai", e)
            else:
                raise ProviderError(str(e), "openai", e)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings using OpenAI API."""
        try:
            response = await self.client.embeddings.create(
                model="text-embedding-3-small",  # or text-embedding-ada-002
                input=texts,
            )

            return [item.embedding for item in response.data]

        except OpenAIError as e:
            raise ProviderError(f"Embedding failed: {e}", "openai", e)

    def token_count(self, text: str) -> int:
        """Count tokens using tiktoken."""
        tokenizer = self._get_tokenizer()
        return len(tokenizer.encode(text))

    async def healthcheck(self) -> bool:
        """Check OpenAI API health."""
        try:
            await self.client.models.list()
            return True
        except Exception:
            return False
