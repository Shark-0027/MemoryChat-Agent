"""Pydantic Settings definitions for MemoryChat-Agent.

All configuration is read from environment variables, optionally backed by a
``.env`` file located at the project root. No API keys or model names are
hardcoded anywhere in the source code.

The :class:`Settings` model groups configuration into logical sections:

    * OpenAI API connection (key, base URL, chat & embedding models).
    * mem0 long-term memory backend (vector store, paths, providers).
    * Application runtime (Streamlit port, logging level, debug flag).

Example:
    >>> from config.settings import get_settings
    >>> cfg = get_settings()
    >>> cfg.openai_model
    'gpt-4o-mini'
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root directory (two levels up from this file: config/ -> project root).
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Central application settings loaded from the environment.

    All fields map to environment variables (case-insensitive). A ``.env`` file
    at the project root is automatically loaded when present.

    Attributes:
        app_name: Application display name shown in the UI.
        app_version: Application version string shown in the UI.
        openai_api_key: Secret OpenAI API key. Required.
        openai_base_url: Base URL for the OpenAI-compatible API endpoint.
        openai_model: Chat completion model identifier.
        openai_embedding_model: Embedding model identifier used by mem0.
        mem0_vector_store: Vector store provider for mem0 (e.g. ``chroma``).
        mem0_vector_store_path: Local filesystem path for the vector store.
        mem0_llm_provider: LLM provider mem0 uses for memory extraction.
        mem0_embedder_provider: Embedder provider mem0 uses for vectors.
        app_port: TCP port the Streamlit server listens on.
        log_level: Logging verbosity level.
        debug: Whether to run the application in debug mode.
    """

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ------------------------------------------------------------------ #
    # OpenAI API Configuration
    # ------------------------------------------------------------------ #
    openai_api_key: SecretStr = Field(
        default=SecretStr(""),
        description="OpenAI API key used for chat completions and embeddings.",
    )
    openai_base_url: str = Field(
        default="https://api.openai.com/v1",
        description="Base URL for the OpenAI-compatible API endpoint.",
    )
    openai_model: str = Field(
        default="gpt-4o-mini",
        description="Chat completion model identifier.",
    )
    openai_embedding_model: str = Field(
        default="text-embedding-3-small",
        description="Embedding model identifier used by mem0.",
    )

    # ------------------------------------------------------------------ #
    # mem0 Memory Configuration
    # ------------------------------------------------------------------ #
    mem0_vector_store: Literal["chroma"] = Field(
        default="chroma",
        description="Vector store provider used by mem0.",
    )
    mem0_vector_store_path: Path = Field(
        default=PROJECT_ROOT / "data" / "chroma",
        description="Local filesystem path for the ChromaDB vector store.",
    )
    mem0_collection_name: str = Field(
        default="mem0",
        description="ChromaDB collection name used by mem0.",
    )
    mem0_llm_provider: str = Field(
        default="openai",
        description="LLM provider mem0 uses for memory extraction.",
    )
    mem0_embedder_provider: str = Field(
        default="openai",
        description="Embedder provider mem0 uses for vector generation.",
    )
    mem0_default_user_id: str = Field(
        default="default_user",
        description="Default user identifier used to scope memories.",
    )

    # ------------------------------------------------------------------ #
    # Application Configuration
    # ------------------------------------------------------------------ #
    app_name: str = Field(
        default="MemoryChat-Agent",
        description="Application display name shown in the UI title and sidebar.",
    )
    app_version: str = Field(
        default="0.1.0",
        description="Application version string shown in the UI.",
    )
    app_port: int = Field(
        default=8501,
        ge=1,
        le=65535,
        description="TCP port the Streamlit server listens on.",
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging verbosity level.",
    )
    debug: bool = Field(
        default=False,
        description="Whether to run the application in debug mode.",
    )

    # ------------------------------------------------------------------ #
    # Validators
    # ------------------------------------------------------------------ #
    @field_validator("mem0_vector_store_path", mode="after")
    @classmethod
    def _ensure_absolute(cls, value: Path) -> Path:
        """Ensure the vector store path is absolute.

        Args:
            value: The path parsed from the environment.

        Returns:
            An absolute :class:`pathlib.Path`.
        """
        return value.resolve() if value.is_absolute() else (PROJECT_ROOT / value).resolve()

    # ------------------------------------------------------------------ #
    # Convenience accessors
    # ------------------------------------------------------------------ #
    @property
    def openai_api_key_get_secret_value(self) -> str:
        """Return the raw OpenAI API key as a string.

        Returns:
            The decrypted API key, or an empty string if unset.
        """
        return self.openai_api_key.get_secret_value()

    @property
    def is_configured(self) -> bool:
        """Whether the minimum required configuration is present.

        Returns:
            ``True`` if an OpenAI API key has been provided.
        """
        return bool(self.openai_api_key.get_secret_value())


# A module-level singleton for convenient imports across the app.
settings: Settings = Settings()  # type: ignore[call-arg]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached :class:`Settings` instance.

    Using ``lru_cache`` guarantees a single instantiation per process,
    which avoids re-reading the environment on every access.

    Returns:
        The shared :class:`Settings` instance.
    """
    return Settings()  # type: ignore[call-arg]
