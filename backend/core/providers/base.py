"""Base provider interface for LLM interactions."""

from abc import ABC, abstractmethod
from typing import Optional, Any
from dataclasses import dataclass
from enum import Enum


class ProviderType(str, Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    KIMI = "kimi"
    LOCAL = "local"


@dataclass
class ProviderConfig:
    """Configuration for an LLM provider."""
    provider_type: ProviderType
    api_key: str
    model: str
    base_url: Optional[str] = None
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    timeout: int = 60
    max_retries: int = 3


@dataclass
class GenerationRequest:
    """Request for text generation."""
    prompt: str
    system: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    tools_allowed: bool = False
    json_schema: Optional[dict] = None
    stop_sequences: Optional[list[str]] = None


@dataclass
class GenerationResponse:
    """Response from text generation."""
    text: str
    model: str
    usage: dict
    finish_reason: str
    raw_response: Optional[Any] = None


class BaseProvider(ABC):
    """
    Abstract base class for LLM providers.

    All providers must implement this interface to ensure consistent
    behavior across different models and APIs.
    """

    def __init__(self, config: ProviderConfig):
        """Initialize the provider with configuration."""
        self.config = config

    @abstractmethod
    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        """
        Generate text based on a prompt.

        Args:
            request: Generation request with prompt and parameters

        Returns:
            Generation response with text and metadata

        Raises:
            ProviderError: If generation fails
        """
        pass

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors

        Raises:
            ProviderError: If embedding fails
        """
        pass

    @abstractmethod
    def token_count(self, text: str) -> int:
        """
        Count tokens in text.

        Args:
            text: Text to count tokens for

        Returns:
            Number of tokens
        """
        pass

    @abstractmethod
    async def healthcheck(self) -> bool:
        """
        Check if the provider is healthy and accessible.

        Returns:
            True if healthy, False otherwise
        """
        pass

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} model={self.config.model}>"


class ProviderError(Exception):
    """Base exception for provider errors."""

    def __init__(self, message: str, provider: str, original_error: Optional[Exception] = None):
        self.message = message
        self.provider = provider
        self.original_error = original_error
        super().__init__(self.message)


class RateLimitError(ProviderError):
    """Raised when rate limit is exceeded."""
    pass


class AuthenticationError(ProviderError):
    """Raised when authentication fails."""
    pass


class InvalidRequestError(ProviderError):
    """Raised when request is invalid."""
    pass


class TimeoutError(ProviderError):
    """Raised when request times out."""
    pass
