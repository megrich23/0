"""Kimi 2 provider implementation."""

import httpx
from typing import Optional

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


class KimiProvider(BaseProvider):
    """
    Provider for Kimi 2 (Moonshot AI) models.

    Kimi 2 is positioned as a drop-in replacement with OpenAI-compatible API.
    """

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.base_url = config.base_url or "https://api.moonshot.cn/v1"
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {config.api_key}",
                "Content-Type": "application/json",
            },
            timeout=config.timeout,
        )

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        """Generate text using Kimi API."""
        try:
            messages = []
            if request.system:
                messages.append({"role": "system", "content": request.system})
            messages.append({"role": "user", "content": request.prompt})

            payload = {
                "model": self.config.model,
                "messages": messages,
                "temperature": request.temperature or self.config.temperature,
            }

            if request.max_tokens:
                payload["max_tokens"] = request.max_tokens
            elif self.config.max_tokens:
                payload["max_tokens"] = self.config.max_tokens

            if request.stop_sequences:
                payload["stop"] = request.stop_sequences

            if request.json_schema:
                payload["response_format"] = {"type": "json_object"}

            response = await self.client.post("/chat/completions", json=payload)

            if response.status_code == 429:
                raise RateLimitError(
                    "Rate limit exceeded",
                    "kimi",
                    Exception(response.text)
                )
            elif response.status_code == 401:
                raise AuthenticationError(
                    "Authentication failed",
                    "kimi",
                    Exception(response.text)
                )
            elif response.status_code >= 400:
                raise InvalidRequestError(
                    f"Request failed: {response.text}",
                    "kimi",
                    Exception(response.text)
                )

            response.raise_for_status()
            data = response.json()

            return GenerationResponse(
                text=data["choices"][0]["message"]["content"],
                model=data["model"],
                usage={
                    "prompt_tokens": data["usage"]["prompt_tokens"],
                    "completion_tokens": data["usage"]["completion_tokens"],
                    "total_tokens": data["usage"]["total_tokens"],
                },
                finish_reason=data["choices"][0]["finish_reason"],
                raw_response=data,
            )

        except httpx.HTTPError as e:
            raise ProviderError(f"HTTP error: {e}", "kimi", e)
        except Exception as e:
            if isinstance(e, (RateLimitError, AuthenticationError, InvalidRequestError)):
                raise
            raise ProviderError(f"Unexpected error: {e}", "kimi", e)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings using Kimi API."""
        try:
            payload = {
                "model": "kimi-embedding",  # Adjust based on actual Kimi embedding model
                "input": texts,
            }

            response = await self.client.post("/embeddings", json=payload)
            response.raise_for_status()
            data = response.json()

            return [item["embedding"] for item in data["data"]]

        except httpx.HTTPError as e:
            raise ProviderError(f"Embedding failed: {e}", "kimi", e)

    def token_count(self, text: str) -> int:
        """
        Approximate token count for Kimi.
        Kimi likely uses a similar tokenizer to GPT.
        """
        # Rough estimate: ~4 characters per token for Chinese/English mix
        return len(text) // 4

    async def healthcheck(self) -> bool:
        """Check Kimi API health."""
        try:
            response = await self.client.get("/models")
            return response.status_code == 200
        except Exception:
            return False

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.client.aclose()
