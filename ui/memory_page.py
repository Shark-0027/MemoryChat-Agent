"""Memory page for the MemoryChat-Agent UI.

Renders the long-term memory management interface. Users can:

* View all stored memories.
* Search memories by semantic query.
* Update a memory's content.
* Delete a single memory.
* Clear all memories.

This module is a UI adapter only — all memory operations go through
:class:`memory.manager.MemoryManager`.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from memory.exceptions import MemoryError, MemoryNotFoundError
from memory.manager import MemoryManager
from ui.components import render_empty_state, render_memory_card


def _get_memory_manager() -> MemoryManager:
    """Return the MemoryManager stored in session state, creating it if needed.

    Returns:
        The :class:`MemoryManager` instance for this session.
    """
    if "memory_manager" not in st.session_state:
        st.session_state.memory_manager = MemoryManager()
    return st.session_state.memory_manager


def _delete_memory(manager: MemoryManager, memory_id: str) -> None:
    """Delete a single memory by id.

    Args:
        manager: The :class:`MemoryManager` instance.
        memory_id: The id of the memory to delete.
    """
    try:
        manager.delete_memory(memory_id)
        st.toast("Memory deleted", icon="🗑️")
    except MemoryNotFoundError:
        st.toast("Memory not found", icon="⚠️")
    except MemoryError as exc:
        st.error(f"Failed to delete memory: {exc}")


def _update_memory(
    manager: MemoryManager,
    memory_id: str,
    new_content: str,
) -> None:
    """Update a memory's content.

    Args:
        manager: The :class:`MemoryManager` instance.
        memory_id: The id of the memory to update.
        new_content: The new memory content text.
    """
    try:
        manager.update_memory(memory_id, new_content)
        st.toast("Memory updated", icon="💾")
    except MemoryError as exc:
        st.error(f"Failed to update memory: {exc}")


def _clear_all_memory(manager: MemoryManager) -> None:
    """Delete all memories for the current user.

    Args:
        manager: The :class:`MemoryManager` instance.
    """
    try:
        manager.clear_memory()
        st.toast("All memories cleared", icon="🧹")
    except MemoryError as exc:
        st.error(f"Failed to clear memories: {exc}")


def render_memory_page() -> None:
    """Render the memory management page.

    Shows a search bar, a list of memory cards (each with update/delete
    controls), and a "clear all" button.
    """
    st.header("🧠 Memory")
    st.caption("View, search, edit, and delete your assistant's long-term memories.")

    manager = _get_memory_manager()

    # --- Search bar ----------------------------------------------------
    col1, col2 = st.columns([4, 1])
    with col1:
        search_query = st.text_input(
            "🔍 Search memories",
            value="",
            placeholder="Type a query and click Search, or leave empty to list all",
            key="memory_search_query",
        )
    with col2:
        st.write("")  # spacer to align with the input
        st.write("")
        search_clicked = st.button("Search", type="primary", use_container_width=True)

    # --- Fetch memories ------------------------------------------------
    try:
        if search_clicked and search_query.strip():
            response = manager.search_memory(query=search_query.strip(), limit=50)
        else:
            response = manager.list_memory(limit=100)
    except MemoryError as exc:
        st.error(f"Failed to load memories: {exc}")
        return

    memories: list[dict[str, Any]] = response.get("results", [])

    # --- Summary + clear-all ------------------------------------------
    col_a, col_b = st.columns([3, 1])
    with col_a:
        st.metric(label="Total Memories", value=len(memories))
    with col_b:
        if memories and st.button(
            "🧹 Clear All", use_container_width=True, type="secondary"
        ):
            _clear_all_memory(manager)
            st.rerun()

    st.divider()

    # --- Memory list ---------------------------------------------------
    if not memories:
        render_empty_state(
            icon="🧠",
            title="No memories yet",
            hint="Start chatting — the agent will automatically save what it learns.",
        )
        return

    for index, memory in enumerate(memories):
        render_memory_card(
            memory=memory,
            index=index,
            on_delete=lambda mid: _delete_memory(manager, mid),
            on_update=lambda mid, content: _update_memory(manager, mid, content),
        )


def clear_memory_session() -> None:
    """Clear all memories via the session's MemoryManager."""
    manager = _get_memory_manager()
    _clear_all_memory(manager)


# Public re-export for app/main.py wiring.
__all__ = ["render_memory_page", "clear_memory_session"]
