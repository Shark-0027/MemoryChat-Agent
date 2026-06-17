"""Custom exceptions for the application agent layer.

All errors raised by :class:`app.agent.ChatAgent` inherit from
:class:`AgentError`, so callers can catch the full family with a single
``except AgentError`` clause while still distinguishing specific failure
modes.
"""

from __future__ import annotations


class AgentError(Exception):
    """Base exception for all ChatAgent-related errors."""


class AgentConfigError(AgentError):
    """Raised when the agent is misconfigured (e.g. missing dependencies)."""


class AgentRuntimeError(AgentError):
    """Raised when a chat turn fails during execution.

    Wraps the underlying memory or LLM error with context about which step
    of the workflow failed.
    """
