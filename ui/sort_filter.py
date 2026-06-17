"""Sort & filter utilities for the Memory Dashboard.

Contains the sort-option registry, the toolbar renderer, and the pure
``apply_sort_filter`` function used by the All Memories tab.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

# ---------------------------------------------------------------------------
# Sort option registry
# ---------------------------------------------------------------------------
SORT_OPTIONS: list[tuple[str, str]] = [
    ("created_desc", "Newest first"),
    ("created_asc", "Oldest first"),
    ("updated_desc", "Recently updated"),
    ("content_asc", "Content (A→Z)"),
    ("content_desc", "Content (Z→A)"),
]


# ---------------------------------------------------------------------------
# Toolbar renderer
# ---------------------------------------------------------------------------
def render_sort_filter_toolbar(
    toolbar_key: str,
    categories: list[str] | None = None,
    show_search: bool = True,
) -> dict[str, Any]:
    """Render a sort + filter toolbar and return the current selections.

    Args:
        toolbar_key: A unique key prefix for this toolbar's widgets.
        categories: Optional list of category names for the filter select.
            If ``None`` or empty, no category filter is shown.
        show_search: If ``True``, render a text search input.

    Returns:
        A dict with keys ``sort_by``, ``category``, ``search``. Missing
        controls yield ``None`` values.
    """
    cols = st.columns([2, 2, 3] if show_search else [2, 2])

    sort_by: str | None = None
    category: str | None = None
    search: str | None = None

    with cols[0]:
        sort_options_map = dict(SORT_OPTIONS)
        sort_by = st.selectbox(
            "Sort",
            options=list(sort_options_map.keys()),
            format_func=lambda key: sort_options_map[key],
            key=f"{toolbar_key}_sort",
        )

    with cols[1]:
        if categories:
            options = ["All"] + categories
            selection = st.selectbox(
                "Category",
                options=options,
                key=f"{toolbar_key}_category",
            )
            category = None if selection == "All" else selection

    if show_search and len(cols) > 2:
        with cols[2]:
            search = st.text_input(
                "Filter (substring)",
                value="",
                placeholder="Type to filter memories…",
                key=f"{toolbar_key}_search",
            )

    return {
        "sort_by": sort_by,
        "category": category,
        "search": search,
    }


# ---------------------------------------------------------------------------
# Pure filter/sort application
# ---------------------------------------------------------------------------
def apply_sort_filter(
    memories: list[dict[str, Any]],
    sort_by: str | None,
    category: str | None,
    search: str | None,
) -> list[dict[str, Any]]:
    """Apply sort + category + substring filter to a memory list.

    Args:
        memories: The memory record list.
        sort_by: One of the :data:`SORT_OPTIONS` keys, or ``None``.
        category: A category name to keep, or ``None`` for all.
        search: A case-insensitive substring to match against the memory
            text, or ``None``/empty for all.

    Returns:
        A new sorted/filtered list (the input is not mutated).
    """
    items = list(memories)

    # Category filter.
    if category:
        filtered: list[dict[str, Any]] = []
        for memory in items:
            metadata = memory.get("metadata") or {}
            if (metadata.get("category") or metadata.get("type")) == category:
                filtered.append(memory)
        items = filtered

    # Substring filter.
    if search and search.strip():
        needle = search.strip().lower()
        items = [
            memory
            for memory in items
            if needle in str(memory.get("memory", "")).lower()
        ]

    # Sort.
    if sort_by == "created_desc":
        items.sort(key=lambda m: m.get("created_at") or "", reverse=True)
    elif sort_by == "created_asc":
        items.sort(key=lambda m: m.get("created_at") or "")
    elif sort_by == "updated_desc":
        items.sort(key=lambda m: m.get("updated_at") or "", reverse=True)
    elif sort_by == "content_asc":
        items.sort(key=lambda m: str(m.get("memory", "")).lower())
    elif sort_by == "content_desc":
        items.sort(key=lambda m: str(m.get("memory", "")).lower(), reverse=True)

    return items


__all__ = ["SORT_OPTIONS", "apply_sort_filter", "render_sort_filter_toolbar"]
