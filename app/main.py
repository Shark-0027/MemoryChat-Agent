"""Streamlit entry point for MemoryChat-Agent.

This module is the UI adapter only — it wires together the page modules
and renders the shared sidebar (system status, navigation, action buttons).
All business logic lives in :mod:`app.agent`, :mod:`memory.manager`, and
:mod:`llm.client`.

Run with::

    uv run streamlit run app/main.py
"""

from __future__ import annotations

import streamlit as st

from config import settings
from memory.exceptions import MemoryError
from memory.manager import MemoryManager
from ui.chat_page import clear_chat, render_chat_page
from ui.components import render_sidebar_actions, render_sidebar_status
from ui.dashboard_page import clear_memory_session, render_dashboard_page
from ui.settings_page import render_settings_page
from ui.stats_page import render_stats_page

# Type alias for page renderer functions.
PageRenderer = callable


# ---------------------------------------------------------------------------
# Page registry
# ---------------------------------------------------------------------------
PAGES: dict[str, PageRenderer] = {
    "💬 Chat": render_chat_page,
    "🧠 Memory Dashboard": render_dashboard_page,
    "📊 Statistics": render_stats_page,
    "⚙️ Settings": render_settings_page,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _get_memory_count() -> int | None:
    """Return the total number of stored memories, or None on failure.

    Returns:
        The memory count, or ``None`` if it could not be retrieved.
    """
    try:
        manager = MemoryManager()
        response = manager.list_memory(limit=10000)
        return len(response.get("results", []))
    except MemoryError:
        return None
    except Exception:  # pragma: no cover - defensive
        return None


def _handle_clear_chat() -> None:
    """Clear the conversation history."""
    clear_chat()


def _handle_clear_memory() -> None:
    """Clear all stored memories."""
    clear_memory_session()
    st.rerun()


# ---------------------------------------------------------------------------
# Page config & layout
# ---------------------------------------------------------------------------
def main() -> None:
    """Render the Streamlit application."""
    st.set_page_config(
        page_title=f"{settings.app_name} — {settings.app_version}",
        page_icon="🧠",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # --- Sidebar: title ------------------------------------------------
    st.sidebar.title(f"🧠 {settings.app_name}")
    st.sidebar.caption(f"v{settings.app_version} — powered by mem0")
    st.sidebar.divider()

    # --- Sidebar: system status ---------------------------------------
    memory_count = _get_memory_count()
    render_sidebar_status(memory_count=memory_count)

    # --- Sidebar: page navigation -------------------------------------
    st.sidebar.markdown("## 🧭 Navigation")
    selected_page = st.sidebar.radio(
        "Go to",
        options=list(PAGES.keys()),
        label_visibility="collapsed",
    )
    st.sidebar.divider()

    # --- Sidebar: action buttons --------------------------------------
    render_sidebar_actions(
        on_clear_chat=_handle_clear_chat,
        on_clear_memory=_handle_clear_memory,
    )

    # --- Sidebar: footer ----------------------------------------------
    st.sidebar.markdown(
        f"""
        <div style="
            text-align: center;
            color: #888;
            font-size: 0.8rem;
            padding-top: 1rem;
        ">
            {settings.app_name}<br>
            Agent Memory Management System
        </div>
        """,
        unsafe_allow_html=True,
    )

    # --- Main content: render the selected page -----------------------
    page_renderer = PAGES[selected_page]
    page_renderer()


if __name__ == "__main__":
    main()
