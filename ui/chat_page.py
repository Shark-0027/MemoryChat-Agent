"""Chat page for the MemoryChat-Agent UI.

Renders the conversational interface where the user chats with the AI
assistant. Messages are augmented with relevant long-term memories retrieved
via mem0 before being sent to the LLM.

This module is a stub; the full implementation arrives in a later phase.
"""

from __future__ import annotations


def render_chat_page() -> None:
    """Render the chat page.

    Displays the conversation history and an input box for new messages.
    Memory retrieval and LLM calls are wired up in the next phase.
    """
    import streamlit as st

    st.header("💬 Chat")
    st.info("The chat interface will be implemented in the next phase.")
