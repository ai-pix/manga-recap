"""Provider registry: turn a config section into a live provider.

Keeps provider construction in one place so stages only ever do
`build_provider(cfg, "vision")` and never import a vendor SDK directly.
"""

from __future__ import annotations

from ..core.config import KNOWN_PROVIDERS, Config, ConfigError
from .base import LLMProvider, RatePacer, RetryPolicy

__all__ = ["build_provider", "KNOWN_PROVIDERS", "LLMProvider"]


def build_provider(config: Config, role: str) -> LLMProvider:
    """Instantiate the provider configured for `role` ("vision" or "script").

    Raises ConfigError with an actionable message for an unknown provider, a
    missing key, or a missing model id.
    """
    if role not in ("vision", "script"):
        raise ConfigError(f"Unknown LLM role '{role}'. Expected 'vision' or 'script'.")

    provider_name = config.get(f"llm.{role}.provider")
    if not provider_name:
        raise ConfigError(
            f"config.yaml is missing llm.{role}.provider. "
            f"Set one of: {', '.join(KNOWN_PROVIDERS)}"
        )
    if provider_name not in KNOWN_PROVIDERS:
        raise ConfigError(
            f"llm.{role}.provider is '{provider_name}', which is not implemented. "
            f"Available: {', '.join(KNOWN_PROVIDERS)}"
        )

    model = config.require(f"llm.{role}.model")
    api_key = config.require_api_key(provider_name)
    retry = _retry_policy(config, role)
    pacer = RatePacer(float(config.get(f"llm.{role}.requests_per_minute", 0.0)))

    if provider_name == "anthropic":
        from .anthropic import AnthropicProvider

        return AnthropicProvider(
            api_key=api_key,
            model=model,
            max_retries=int(config.get(f"llm.{role}.max_retries", 3)),
            retry=retry,
        )

    if provider_name == "gemini":
        from .gemini import GeminiProvider

        return GeminiProvider(
            api_key=api_key,
            model=model,
            max_retries=int(config.get(f"llm.{role}.max_retries", 3)),
            retry=retry,
            pacer=pacer,
        )

    from .openrouter import OpenRouterProvider

    return OpenRouterProvider(
        api_key=api_key,
        model=model,
        max_retries=int(config.get(f"llm.{role}.max_retries", 3)),
        retry=retry,
        pacer=pacer,
        app_url=config.get("llm.openrouter_app_url"),
    )


def _retry_policy(config: Config, role: str) -> RetryPolicy:
    """Retry behaviour for a role.

    The per-role `llm.<role>.max_retries` wins over the shared
    `llm.retry.max_retries`, because the two roles do not face the same load: the
    vision role sends eight images per call and is the one that meets a busy
    provider, while the script role sends one large text payload.

    Passing an explicit policy into a provider used to make the per-role value
    dead config, because the provider prefers a supplied policy over its own
    argument. Reading the role's value here rather than in the constructor is
    what makes the documented key do anything.
    """
    shared = config.get("llm.retry.max_retries", 3)
    return RetryPolicy(
        max_retries=int(config.get(f"llm.{role}.max_retries", shared)),
        initial_backoff=float(config.get("llm.retry.initial_backoff_seconds", 2.0)),
        max_backoff=float(config.get("llm.retry.max_backoff_seconds", 60.0)),
        multiplier=float(config.get("llm.retry.backoff_multiplier", 2.0)),
    )
