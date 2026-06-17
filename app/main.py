"""Streamlit application entry point.

This module bootstraps the MemoryChat-Agent web UI. It configures the page
layout, renders the sidebar navigation, and dispatches to the appropriate
page module (chat, memory, or config).

Business logic will be implemented in a subsequent phase. For now this module
provides a minimal runnable shell so the app starts without errors.

Example:
    Run the app locally::

        uv run streamlit run app/main.py
"""

from __future__ import annotations

import logging

import streamlit as st

from config import settings
from utils.logger import get_logger

logger: logging.Logger = get_logger(__name__)


def main() -> None:
    """Render the MemoryChat-Agent Streamlit application.

    Sets up the page configuration, sidebar navigation, and delegates rendering
    to the selected page module. The status bar is always visible.
    """
    st.set_page_config(
        page_title="MemoryChat-Agent",
        page_icon="🧠",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.title("MemoryChat-Agent")
    st.caption("An AI Assistant with Long-Term Memory powered by mem0")

    # ------------------------------------------------------------------ #
    # Sidebar navigation (placeholder; pages wired up in the next phase).
    # ------------------------------------------------------------------ #
    st.sidebar.title("Navigation")
    page: str = st.sidebar.radio(
        "Go to",
        options=["Chat", "Memory", "Config"],
        index=0,
    )

    # Status bar showing current configuration health.
    _render_status_bar()

    # Page dispatch — full implementations arrive in the next phase.
    if page == "Chat":
        st.info("💬 The Chat page will be implemented in the next phase.")
    elif page == "Memory":
        st.info("🧠 The Memory page will be implemented in the next phase.")
    elif page == "Config":
        st.info("⚙️ The Config page will be implemented in the next phase.")


def _render_status_bar() -> None:
    """Render a lightweight status bar with configuration health info.

    Displays whether the OpenAI API key is set and the configured model.
    """
    status_col, model_col = st.columns([1, 2])
    with status_col:
        if settings.is_configured:
            st.success("API key configured")
        else:
            st.warning("API key missing — set OPENAI_API_KEY in .env")
    with model_col:
        st.caption(
            f"Model: `{settings.openai_model}` · "
            f"Embedding: `{settings.openai_embedding_model}`"
        )


if __name__ == "__main__":
    main()
