"""Custom exceptions for the LLM subsystem.

All LLM-related errors raised by :class:`llm.client.LLMClient` inherit from
:class:`LLMError`, so callers can catch the full family with a single
``except LLMError`` clause while still distinguishing specific failure modes.
"""

from __future__ import annotations


class LLMError(Exception):
    """Base exception for all LLM-related errors."""


class LLMConfigError(LLMError):
    """Raised when the LLM subsystem is misconfigured.

    For example: missing API key or invalid base URL.
    """


class LLMInitializationError(LLMError):
    """Raised when the OpenAI client cannot be initialized."""


class LLMRequestError(LLMError):
    """Raised when a chat-completion request fails.

    Wraps the underlying OpenAI SDK error with context about which operation
    was attempted (chat vs stream_chat).
    """


class LLMResponseError(LLMError):
    """Raised when the LLM returns an empty or malformed response."""
