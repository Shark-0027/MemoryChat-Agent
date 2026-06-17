"""Shared helpers for the Memory Dashboard tabs.

This module centralizes the session-state plumbing and per-row action
handlers used across the four Dashboard tabs (All Memories, Search, Add,
Batch). Keeping it separate keeps each tab module under 300 lines.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from memory.exceptions import MemoryError, MemoryNotFoundError
from memory.manager import MemoryManager

# Page size for the All Memories pagination.
PAGE_SIZE: int = 10

# Session-state keys.
CACHE_KEY: str = "dashboard_memories_cache"
SELECTED_KEY: str = "dashboard_selected"
PAGE_KEY: str = "dashboard_page"


# ---------------------------------------------------------------------------
# Session-state helpers
# ---------------------------------------------------------------------------
def get_memory_manager() -> MemoryManager:
    """Return the session-scoped MemoryManager, creating it if needed.

    Returns:
        The :class:`MemoryManager` instance for this session.
    """
    if "memory_manager" not in st.session_state:
        st.session_state.memory_manager = MemoryManager()
    return st.session_state.memory_manager


def fetch_all_memories(manager: MemoryManager) -> list[dict[str, Any]]:
    """Fetch all memories for the current user (no caching).

    Args:
        manager: The :class:`MemoryManager` instance.

    Returns:
        A list of memory record dicts (empty on error).
    """
    try:
        response = manager.list_memory(limit=10000)
    except MemoryError as exc:
        st.error(f"Failed to load memories: {exc}")
        return []
    return response.get("results", [])


def invalidate_cache() -> None:
    """Clear the cached memory list so the next render re-fetches."""
    st.session_state.pop(CACHE_KEY, None)


def get_cached_memories(manager: MemoryManager) -> list[dict[str, Any]]:
    """Return cached memories, fetching them on first access.

    Args:
        manager: The :class:`MemoryManager` instance.

    Returns:
        A list of memory record dicts.
    """
    if CACHE_KEY not in st.session_state:
        st.session_state[CACHE_KEY] = fetch_all_memories(manager)
    return st.session_state[CACHE_KEY]


def get_selected_ids() -> set[str]:
    """Return the live set of selected memory ids from session state.

    Returns:
        A set of memory id strings.
    """
    return set(st.session_state.get(SELECTED_KEY, set()))


def set_selected_ids(ids: set[str]) -> None:
    """Overwrite the selected-ids set in session state.

    Args:
        ids: The new set of selected memory ids.
    """
    st.session_state[SELECTED_KEY] = ids


def extract_categories(memories: list[dict[str, Any]]) -> list[str]:
    """Return the sorted unique category names from a memory list.

    Args:
        memories: The memory record list.

    Returns:
        A sorted list of category strings.
    """
    categories: set[str] = set()
    for memory in memories:
        metadata = memory.get("metadata") or {}
        category = metadata.get("category") or metadata.get("type")
        if category:
            categories.add(str(category))
    return sorted(categories)


def current_page_ids(filtered: list[dict[str, Any]]) -> list[str]:
    """Return the ids on the current page.

    Args:
        filtered: The full filtered memory list.

    Returns:
        A list of memory ids on the current page.
    """
    page = int(st.session_state.get(PAGE_KEY, 1))
    page_start = (page - 1) * PAGE_SIZE
    page_end = page_start + PAGE_SIZE
    return [m.get("id", "") for m in filtered[page_start:page_end]]


# ---------------------------------------------------------------------------
# Per-row actions
# ---------------------------------------------------------------------------
def handle_delete(manager: MemoryManager, memory_id: str) -> None:
    """Delete a single memory and refresh the dashboard.

    Args:
        manager: The :class:`MemoryManager` instance.
        memory_id: The id of the memory to delete.
    """
    try:
        manager.delete_memory(memory_id)
        st.toast("Memory deleted", icon="🗑️")
        invalidate_cache()
        st.rerun()
    except MemoryNotFoundError:
        st.toast("Memory not found", icon="⚠️")
        invalidate_cache()
        st.rerun()
    except MemoryError as exc:
        st.error(f"Failed to delete memory: {exc}")


def handle_update(
    manager: MemoryManager,
    memory_id: str,
    new_content: str,
    new_category: str,
    new_tags: str,
    original: dict[str, Any],
) -> None:
    """Update a memory's content and metadata, then refresh.

    Args:
        manager: The :class:`MemoryManager` instance.
        memory_id: The id of the memory to update.
        new_content: The new memory text.
        new_category: The new category string (may be empty).
        new_tags: A comma-separated tag string (may be empty).
        original: The original memory record (for metadata preservation).
    """
    tags_list = [t.strip() for t in new_tags.split(",") if t.strip()]
    original_metadata = dict(original.get("metadata") or {})
    if new_category:
        original_metadata["category"] = new_category
    else:
        original_metadata.pop("category", None)
    if tags_list:
        original_metadata["tags"] = tags_list
    else:
        original_metadata.pop("tags", None)

    try:
        manager.update_memory(memory_id, new_content, metadata=original_metadata)
        st.toast("Memory updated", icon="💾")
        invalidate_cache()
        st.rerun()
    except MemoryError as exc:
        st.error(f"Failed to update memory: {exc}")


__all__ = [
    "PAGE_KEY",
    "PAGE_SIZE",
    "current_page_ids",
    "extract_categories",
    "fetch_all_memories",
    "get_cached_memories",
    "get_memory_manager",
    "get_selected_ids",
    "handle_delete",
    "handle_update",
    "invalidate_cache",
    "set_selected_ids",
]
