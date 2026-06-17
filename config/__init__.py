"""Application configuration package.

This package centralizes all runtime configuration for MemoryChat-Agent.
Settings are loaded from environment variables (and a local ``.env`` file)
via :mod:`pydantic_settings`, ensuring no secrets are hardcoded in source.

Typical usage::

    from config import settings

    print(settings.openai_api_key)
    print(settings.openai_model)

Attributes:
    settings: The singleton :class:`Settings` instance used across the app.
"""

from config.settings import Settings, get_settings, settings

__all__ = ["Settings", "get_settings", "settings"]
