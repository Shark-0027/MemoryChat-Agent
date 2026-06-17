"""Add Memory tab for the Memory Dashboard.

Renders a form for manually adding a long-term memory with optional
category and tags metadata.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from memory.manager import MemoryManager
from ui.dashboard_helpers import invalidate_cache
from ui.widgets import safe_call


def render_add_memory_tab(manager: MemoryManager) -> None:
    """Render the manual add-memory tab.

    Args:
        manager: The :class:`MemoryManager` instance.
    """
    st.subheader("➕ Add Memory")
    st.caption("Manually add a long-term memory. mem0 will store it as-is.")

    content = st.text_area(
        "Memory content",
        value="",
        height=100,
        placeholder="e.g. The user prefers concise answers with code examples.",
        key="dashboard_add_content",
    )
    col_cat, col_tags = st.columns(2)
    with col_cat:
        category = st.text_input(
            "Category (optional)",
            value="",
            placeholder="e.g. preference",
            key="dashboard_add_category",
        )
    with col_tags:
        tags = st.text_input(
            "Tags (comma-separated, optional)",
            value="",
            placeholder="e.g. style, communication",
            key="dashboard_add_tags",
        )

    if st.button(
        "➕ Add Memory",
        type="primary",
        key="dashboard_add_btn",
        disabled=not content.strip(),
    ):
        tags_list = [t.strip() for t in tags.split(",") if t.strip()]
        metadata: dict[str, Any] = {}
        if category.strip():
            metadata["category"] = category.strip()
        if tags_list:
            metadata["tags"] = tags_list

        response = safe_call(
            manager.add_memory,
            messages=content.strip(),
            metadata=metadata or None,
            infer=False,
            success_message="Memory added",
            error_prefix="Add failed",
        )
        if response is not None:
            invalidate_cache()
            st.rerun()


__all__ = ["render_add_memory_tab"]
