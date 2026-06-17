"""LLM client package for MemoryChat-Agent.

Wraps the OpenAI SDK to provide chat completions (blocking and streaming)
and centralized system-prompt templates.

All Agent layers that need LLM access must go through :class:`LLMClient` —
never call the OpenAI SDK directly.

Modules:
    client: The :class:`LLMClient` wrapping the OpenAI chat-completion API.
    prompts: System prompt templates and the :func:`build_system_prompt` helper.
    exceptions: Custom exception hierarchy for LLM errors.

Example:
    >>> from llm.client import LLMClient
    >>> from llm.prompts import build_system_prompt
    >>> client = LLMClient()
    >>> system = build_system_prompt(memories=["Prefers dark mode"])
    >>> reply = client.chat(
    ...     messages=[
    ...         {"role": "system", "content": system},
    ...         {"role": "user", "content": "Hi"},
    ...     ],
    ... )
"""

from llm.client import LLMClient, Message
from llm.exceptions import (
    LLMConfigError,
    LLMError,
    LLMInitializationError,
    LLMRequestError,
    LLMResponseError,
)
from llm.prompts import (
    MEMORY_CONTEXT_TEMPLATE,
    SYSTEM_PROMPT_BASE,
    build_system_prompt,
)

__all__ = [
    "LLMClient",
    "Message",
    "LLMError",
    "LLMConfigError",
    "LLMInitializationError",
    "LLMRequestError",
    "LLMResponseError",
    "SYSTEM_PROMPT_BASE",
    "MEMORY_CONTEXT_TEMPLATE",
    "build_system_prompt",
]
