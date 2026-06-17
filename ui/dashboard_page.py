"""Memory Dashboard page for the MemoryChat-Agent UI.

The Dashboard is the primary management surface for long-term memories.
It is organized into four tabs:

* **All Memories** — paginated, sortable, filterable table with per-row
  edit/delete actions and multi-select for batch operations.
* **Search** — semantic search via :meth:`MemoryManager.search_memory`
  with similarity scores and metadata.
* **Add Memory** — manual entry of a new long-term memory.
* **Batch Operations** — bulk delete, export to JSON, and import from
  JSON.

All memory operations go through :class:`memory.manager.MemoryManager` —
the UI never touches mem0 directly. The per-tab rendering logic lives in
sibling modules (``dashboard_all_tab.py``, ``dashboard_search_tab.py``,
``dashboard_add_tab.py``, ``dashboard_batch_tab.py``) to keep each file
under 300 lines.
"""

from __future__ import annotations

import streamlit as st

from memory.exceptions import MemoryError
from ui.dashboard_add_tab import render_add_memory_tab
from ui.dashboard_all_tab import render_all_memories_tab
from ui.dashboard_batch_tab import render_batch_tab
from ui.dashboard_helpers import get_memory_manager, invalidate_cache
from ui.dashboard_search_tab import render_search_tab


def render_dashboard_page() -> None:
    """Render the Memory Dashboard page with four tabs."""
    st.header("🧠 Memory Dashboard")
    st.caption(
        "View, search, edit, delete, and batch-manage your assistant's "
        "long-term memories."
    )

    manager = get_memory_manager()

    tab_all, tab_search, tab_add, tab_batch = st.tabs(
        ["📋 All Memories", "🔍 Search", "➕ Add Memory", "📦 Batch"]
    )
    with tab_all:
        render_all_memories_tab(manager)
    with tab_search:
        render_search_tab(manager)
    with tab_add:
        render_add_memory_tab(manager)
    with tab_batch:
        render_batch_tab(manager)


def clear_memory_session() -> None:
    """Clear all memories via the session's MemoryManager (sidebar hook)."""
    manager = get_memory_manager()
    try:
        manager.clear_memory()
        st.toast("All memories cleared", icon="🧹")
    except MemoryError as exc:
        st.error(f"Failed to clear memories: {exc}")
    invalidate_cache()


__all__ = ["render_dashboard_page", "clear_memory_session"]
