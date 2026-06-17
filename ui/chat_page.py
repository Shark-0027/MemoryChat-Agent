"""Chat page for the MemoryChat-Agent UI.

Renders the conversational interface where the user chats with the AI
assistant. Each user message triggers the full ChatAgent workflow:
memory retrieval → prompt construction → LLM call → memory extraction →
persistence → streaming reply.

This module is a UI adapter only — all business logic lives in
:class:`app.agent.ChatAgent`.
"""

from __future__ import annotations

import streamlit as st

from app.agent import ChatAgent
from app.exceptions import AgentRuntimeError
from ui.components import (
    render_assistant_message,
    render_assistant_stream,
    render_empty_state,
    render_user_message,
)


def _get_agent() -> ChatAgent:
    """Return the ChatAgent stored in session state, creating it if needed.

    Returns:
        The :class:`ChatAgent` instance for this session.
    """
    if "agent" not in st.session_state:
        st.session_state.agent = ChatAgent()
    return st.session_state.agent


def _get_messages() -> list[dict[str, str]]:
    """Return the conversation history from session state.

    Returns:
        A list of message dicts (role/content).
    """
    if "messages" not in st.session_state:
        st.session_state.messages = []
    return st.session_state.messages


def _handle_user_input(agent: ChatAgent, messages: list[dict[str, str]]) -> None:
    """Handle a new user message: render, call agent, persist, render reply.

    Args:
        agent: The :class:`ChatAgent` instance.
        messages: The conversation history list (mutated in place).
    """
    prompt = st.session_state.user_input
    if not prompt or not prompt.strip():
        return

    # Render and store the user message.
    render_user_message(prompt)
    messages.append({"role": "user", "content": prompt})

    # Call the agent with streaming output.
    # History excludes the just-added user message (the agent adds it itself).
    history = list(messages[:-1])
    try:
        stream = agent.stream_chat(
            user_message=prompt,
            history=history,
        )
        reply = render_assistant_stream(stream)
    except AgentRuntimeError as exc:
        reply = f"⚠️ Sorry, an error occurred: {exc}"
        render_assistant_message(reply)

    messages.append({"role": "assistant", "content": reply})


def render_chat_page() -> None:
    """Render the chat page.

    Displays the conversation history and a chat input box. New messages
    are processed through the :class:`ChatAgent` workflow with streaming
    output.
    """
    st.header("💬 Chat")
    st.caption("Chat with your AI assistant — it remembers what matters.")

    agent = _get_agent()
    messages = _get_messages()

    # Empty-state hint.
    if not messages:
        render_empty_state(
            icon="💬",
            title="Start a conversation",
            hint="Type a message below. The agent will remember context across turns.",
        )

    # Render conversation history.
    for message in messages:
        if message["role"] == "user":
            render_user_message(message["content"])
        else:
            render_assistant_message(message["content"])

    # Input box — Streamlit's chat_input returns the text when submitted.
    prompt = st.chat_input("Type your message...")
    if prompt:
        st.session_state.user_input = prompt
        _handle_user_input(agent, messages)


def clear_chat() -> None:
    """Clear the conversation history from session state."""
    st.session_state.messages = []
    st.toast("Chat cleared!", icon="🗑️")


# Public re-export for app/main.py wiring.
__all__ = ["render_chat_page", "clear_chat"]
