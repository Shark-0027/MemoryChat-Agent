"""Application package for MemoryChat-Agent.

This package contains the application's business logic, including the
:class:`ChatAgent` orchestrator that ties together the LLM and memory
subsystems. The Streamlit UI layer is a thin adapter that calls into this
package — no business logic lives in the UI.

Modules:
    agent: The :class:`ChatAgent` that orchestrates the memory-augmented
        conversational workflow.
    exceptions: Custom exception hierarchy for agent errors.
    main: The Streamlit entry point (UI adapter only).

Example:
    >>> from app.agent import create_agent
    >>> agent = create_agent(user_id="alice")
    >>> reply = agent.chat("Hi, I prefer dark mode.")
"""

from app.agent import ChatAgent, create_agent
from app.exceptions import AgentConfigError, AgentError, AgentRuntimeError

__all__ = [
    "ChatAgent",
    "create_agent",
    "AgentError",
    "AgentConfigError",
    "AgentRuntimeError",
]
