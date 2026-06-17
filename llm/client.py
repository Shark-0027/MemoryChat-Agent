"""OpenAI LLM client wrapper.

This module provides :class:`LLMClient`, a typed, UI-independent wrapper
around the OpenAI SDK. All configuration is sourced from
:data:`config.settings` — no API keys, model names, or base URLs are
hardcoded.

The client supports:

* Synchronous chat completions via :meth:`LLMClient.chat`.
* Streaming chat completions via :meth:`LLMClient.stream_chat`.
* Automatic system-prompt composition with injected memories
  (see :mod:`llm.prompts`).

Example:
    >>> from llm.client import LLMClient
    >>> from llm.prompts import build_system_prompt
    >>> client = LLMClient()
    >>> system = build_system_prompt(memories=["Prefers dark mode"])
    >>> reply = client.chat(
    ...     messages=[
    ...         {"role": "system", "content": system},
    ...         {"role": "user", "content": "What UI theme do I like?"},
    ...     ],
    ... )
    >>> print(reply)
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from typing import Any

from config import settings
from llm.exceptions import (
    LLMConfigError,
    LLMInitializationError,
    LLMRequestError,
    LLMResponseError,
)
from utils.logger import get_logger

logger: logging.Logger = get_logger(__name__)

# Type alias for the lazily-initialized OpenAI client.
OpenAIClient = Any

# Type alias for a single chat message dict (role/content).
Message = dict[str, str]


class LLMClient:
    """Wrapper around the OpenAI chat-completion client.

    The client lazily initializes the OpenAI SDK on first use and exposes
    both blocking and streaming chat-completion methods. All parameters
    (model, temperature, max_tokens, base_url) default to values from
    :data:`config.settings` but can be overridden per call.

    Attributes:
        _client: The lazily-initialized OpenAI client instance.
    """

    def __init__(self) -> None:
        """Initialize the LLM client without connecting yet."""
        self._client: OpenAIClient | None = None

    # ------------------------------------------------------------------ #
    # Public properties
    # ------------------------------------------------------------------ #
    @property
    def client(self) -> OpenAIClient:
        """Return the OpenAI client, initializing it on first access.

        Returns:
            The initialized OpenAI client instance.

        Raises:
            LLMInitializationError: If the client cannot be initialized.
        """
        if self._client is None:
            self._client = self._init_client()
        return self._client

    # ------------------------------------------------------------------ #
    # Client initialization
    # ------------------------------------------------------------------ #
    def _init_client(self) -> OpenAIClient:
        """Initialize and return the OpenAI client.

        Returns:
            The configured OpenAI client instance.

        Raises:
            LLMConfigError: If the API key is not configured.
            LLMInitializationError: If initialization fails for another reason.
        """
        if not settings.is_configured:
            raise LLMConfigError(
                "OPENAI_API_KEY is not configured. Set it in .env before using the LLM."
            )

        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - dependency is declared
            raise LLMInitializationError(
                "openai is not installed. Run `uv sync` to install dependencies."
            ) from exc

        try:
            api_key: str = settings.openai_api_key.get_secret_value()
            logger.info(
                "Initializing OpenAI client (base_url=%s, model=%s)",
                settings.openai_base_url,
                settings.openai_model,
            )
            client = OpenAI(
                api_key=api_key,
                base_url=settings.openai_base_url,
            )
            logger.info("OpenAI client initialized successfully")
            return client
        except Exception as exc:
            raise LLMInitializationError(
                f"Failed to initialize OpenAI client: {exc}"
            ) from exc

    # ------------------------------------------------------------------ #
    # Public API — chat completions
    # ------------------------------------------------------------------ #
    def chat(
        self,
        messages: list[Message],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> str:
        """Generate a chat completion (blocking).

        Args:
            messages: The conversation messages (role/content dicts).
            model: Model identifier. If ``None``, uses the configured default.
            temperature: Sampling temperature in ``[0, 2]``.
            max_tokens: Maximum tokens to generate. If ``None``, the API
                default is used.

        Returns:
            The assistant's reply text.

        Raises:
            LLMRequestError: If the API request fails.
            LLMResponseError: If the response is empty or malformed.
        """
        used_model = model or settings.openai_model
        logger.info(
            "Chat request (model=%s, temperature=%.2f, max_tokens=%s, messages=%d)",
            used_model,
            temperature,
            max_tokens,
            len(messages),
        )

        try:
            response = self.client.chat.completions.create(
                model=used_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as exc:
            raise LLMRequestError(f"Chat request failed: {exc}") from exc

        content = _extract_content(response)
        logger.info("Chat response received (%d chars)", len(content))
        logger.debug("Response content: %s", content)
        return content

    def stream_chat(
        self,
        messages: list[Message],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> Iterator[str]:
        """Generate a streaming chat completion, yielding text chunks.

        Args:
            messages: The conversation messages (role/content dicts).
            model: Model identifier. If ``None``, uses the configured default.
            temperature: Sampling temperature in ``[0, 2]``.
            max_tokens: Maximum tokens to generate. If ``None``, the API
                default is used.

        Yields:
            Successive text chunks (deltas) from the assistant's reply.

        Raises:
            LLMRequestError: If the API request fails.
        """
        used_model = model or settings.openai_model
        logger.info(
            "Stream chat request (model=%s, temperature=%.2f, max_tokens=%s, messages=%d)",
            used_model,
            temperature,
            max_tokens,
            len(messages),
        )

        try:
            stream = self.client.chat.completions.create(
                model=used_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
        except Exception as exc:
            raise LLMRequestError(f"Stream chat request failed: {exc}") from exc

        total_chars = 0
        for chunk in stream:
            delta = _extract_delta(chunk)
            if delta:
                total_chars += len(delta)
                yield delta

        logger.info("Stream chat completed (%d chars total)", total_chars)

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #
    def close(self) -> None:
        """Release resources held by the OpenAI client.

        Safe to call multiple times. After closing, the next chat operation
        will re-initialize the client.
        """
        if self._client is not None:
            try:
                # The OpenAI SDK client has a `close()` method.
                self._client.close()
                logger.info("OpenAI client closed")
            except Exception as exc:  # pragma: no cover - best-effort cleanup
                logger.warning("Error closing OpenAI client: %s", exc)
            finally:
                self._client = None


# ---------------------------------------------------------------------------
# Internal helpers — response extraction
# ---------------------------------------------------------------------------
def _extract_content(response: Any) -> str:
    """Extract the assistant's text content from a chat-completion response.

    Args:
        response: The ``ChatCompletion`` object returned by the OpenAI SDK.

    Returns:
        The reply text string.

    Raises:
        LLMResponseError: If the response has no choices or empty content.
    """
    try:
        choices = response.choices
        if not choices:
            raise LLMResponseError("Chat completion response has no choices.")
        content = choices[0].message.content
        if content is None:
            raise LLMResponseError("Chat completion response content is None.")
        return content
    except (AttributeError, IndexError) as exc:
        raise LLMResponseError(f"Malformed chat completion response: {exc}") from exc


def _extract_delta(chunk: Any) -> str:
    """Extract the text delta from a streaming chat-completion chunk.

    Args:
        chunk: A ``ChatCompletionChunk`` object from the stream.

    Returns:
        The delta text string, or an empty string if the chunk carries no
        content (e.g. role-only or final usage chunks).
    """
    try:
        choices = chunk.choices
        if not choices:
            return ""
        delta = choices[0].delta
        if delta is None:
            return ""
        content = delta.content
        return content or ""
    except (AttributeError, IndexError):
        return ""
