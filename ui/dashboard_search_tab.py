"""Search tab for the Memory Dashboard.

Renders a semantic search interface backed by
:meth:`MemoryManager.search_memory`, with similarity scores and metadata.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from memory.manager import MemoryManager
from ui.components import render_empty_state
from ui.widgets import safe_call


def render_search_tab(manager: MemoryManager) -> None:
    """Render the semantic search tab.

    Args:
        manager: The :class:`MemoryManager` instance.
    """
    st.subheader("🔍 Semantic Search")
    st.caption("Search memories by meaning, not just keywords.")

    col_query, col_limit, col_threshold = st.columns([5, 1, 1])
    with col_query:
        query = st.text_input(
            "Query",
            value="",
            placeholder="Describe what you're looking for…",
            key="dashboard_search_query",
        )
    with col_limit:
        limit = st.number_input(
            "Limit",
            min_value=1,
            max_value=100,
            value=10,
            step=1,
            key="dashboard_search_limit",
        )
    with col_threshold:
        threshold = st.slider(
            "Min score",
            min_value=0.0,
            max_value=1.0,
            value=0.1,
            step=0.05,
            key="dashboard_search_threshold",
        )

    if not query.strip():
        render_empty_state(
            icon="🔍",
            title="Type a query to search",
            hint="Semantic search ranks memories by relevance.",
        )
        return

    if not st.button("Search", type="primary", key="dashboard_search_btn"):
        return

    response = safe_call(
        manager.search_memory,
        query=query.strip(),
        limit=int(limit),
        threshold=float(threshold),
        error_prefix="Search failed",
    )
    if response is None:
        return

    results = response.get("results", [])
    if not results:
        render_empty_state(
            icon="🔍",
            title="No matches",
            hint="Try a different query or lower the minimum score.",
        )
        return

    st.success(f"Found {len(results)} matching memor(ies).")
    for index, memory in enumerate(results):
        _render_search_result(memory, index)


def _render_search_result(memory: dict[str, Any], index: int) -> None:
    """Render a single search result with score and metadata.

    Args:
        memory: The search result dict (includes ``score``).
        index: The result index (for unique widget keys).
    """
    content = memory.get("memory", "")
    score = memory.get("score")
    memory_id = memory.get("id", "unknown")
    metadata = memory.get("metadata") or {}

    with st.container(border=True):
        st.markdown(f"**{content}**")
        meta_parts: list[str] = [f"🆔 `{memory_id}`"]
        if score is not None:
            meta_parts.append(f"🎯 score: {float(score):.3f}")
        category = metadata.get("category") or metadata.get("type")
        if category:
            meta_parts.append(f"🏷️ {category}")
        created_at = memory.get("created_at")
        if created_at:
            meta_parts.append(f"🕒 {created_at}")
        st.caption(" · ".join(meta_parts))

        if score is not None:
            clamped = min(max(float(score), 0.0), 1.0)
            st.progress(clamped, text=f"{float(score):.1%} match")


__all__ = ["render_search_tab"]
