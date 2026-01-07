"""Factory for creating LLM providers."""

import os
from typing import Optional
import yaml

from .base import BaseProvider, ProviderConfig, ProviderType
from .openai_provider import OpenAIProvider
from .anthropic_provider import AnthropicProvider
from .kimi_provider import KimiProvider


class ProviderFactory:
    """Factory for creating and managing LLM providers."""

    _providers: dict[str, BaseProvider] = {}
    _config: Optional[dict] = None

    @classmethod
    def load_config(cls, config_path: str = "config/providers.yaml") -> None:
        """Load provider configuration from YAML file."""
        with open(config_path, "r") as f:
            cls._config = yaml.safe_load(f)

    @classmethod
    def create_provider(
        cls,
        provider_name: Optional[str] = None,
        provider_type: Optional[ProviderType] = None,
        **kwargs
    ) -> BaseProvider:
        """
        Create a provider instance.

        Args:
            provider_name: Name of configured provider (from config file)
            provider_type: Type of provider (if creating directly)
            **kwargs: Additional configuration overrides

        Returns:
            Provider instance

        Raises:
            ValueError: If configuration is invalid
        """
        # If provider_name is given, use configuration
        if provider_name:
            if cls._config is None:
                cls.load_config()

            provider_config = cls._config.get("providers", {}).get(provider_name)
            if not provider_config:
                raise ValueError(f"Provider '{provider_name}' not found in configuration")

            # Resolve environment variables
            api_key = provider_config.get("api_key")
            if api_key and api_key.startswith("${") and api_key.endswith("}"):
                env_var = api_key[2:-1]
                api_key = os.getenv(env_var)
                if not api_key:
                    raise ValueError(f"Environment variable {env_var} not set")

            provider_type = ProviderType(provider_config.get("type", provider_name))
            model = provider_config.get("model")
            base_url = provider_config.get("base_url")
            temperature = provider_config.get("temperature", 0.7)
            max_tokens = provider_config.get("max_tokens")

            config = ProviderConfig(
                provider_type=provider_type,
                api_key=api_key,
                model=model,
                base_url=base_url,
                temperature=temperature,
                max_tokens=max_tokens,
            )

        # Otherwise, create from direct parameters
        else:
            if not provider_type:
                raise ValueError("Either provider_name or provider_type must be specified")

            config = ProviderConfig(
                provider_type=provider_type,
                **kwargs
            )

        # Create appropriate provider instance
        if config.provider_type == ProviderType.OPENAI:
            return OpenAIProvider(config)
        elif config.provider_type == ProviderType.ANTHROPIC:
            return AnthropicProvider(config)
        elif config.provider_type == ProviderType.KIMI:
            return KimiProvider(config)
        else:
            raise ValueError(f"Unsupported provider type: {config.provider_type}")

    @classmethod
    def get_provider(cls, name: str, cache: bool = True) -> BaseProvider:
        """
        Get a provider instance (cached by default).

        Args:
            name: Provider name from configuration
            cache: Whether to cache the provider instance

        Returns:
            Provider instance
        """
        if cache and name in cls._providers:
            return cls._providers[name]

        provider = cls.create_provider(provider_name=name)

        if cache:
            cls._providers[name] = provider

        return provider

    @classmethod
    def get_agent_provider(cls, agent_name: str) -> BaseProvider:
        """
        Get the configured provider for a specific agent.

        Args:
            agent_name: Name of the agent (planner, writer, critic, etc.)

        Returns:
            Provider instance for that agent
        """
        if cls._config is None:
            cls.load_config()

        # Get agent-specific model assignment
        agent_models = cls._config.get("agent_models", {})
        provider_name = agent_models.get(agent_name)

        if not provider_name:
            # Fall back to default provider
            provider_name = cls._config.get("providers", {}).get("default", "openai")

        return cls.get_provider(provider_name)


# Convenience function
def get_provider(name: str = "default", cache: bool = True) -> BaseProvider:
    """
    Get a provider instance.

    Args:
        name: Provider name from configuration
        cache: Whether to cache the provider instance

    Returns:
        Provider instance
    """
    return ProviderFactory.get_provider(name, cache)
