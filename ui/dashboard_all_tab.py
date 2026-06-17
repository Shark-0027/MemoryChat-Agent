"""All Memories tab for the Memory Dashboard.

Renders a paginated, sortable, filterable list of memory cards with
per-row edit/delete actions and multi-select for batch operations.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from memory.manager import MemoryManager
from ui.components import render_empty_state
from ui.dashboard_helpers import (
    PAGE_SIZE,
    current_page_ids,
    extract_categories,
    get_cached_memories,
    get_selected_ids,
    handle_delete,
    handle_update,
    invalidate_cache,
    set_selected_ids,
)
from ui.sort_filter import apply_sort_filter, render_sort_filter_toolbar
from ui.widgets import (
    render_pagination,
    safe_call,
)


def render_all_memories_tab(manager: MemoryManager) -> None:
    """Render the All Memories tab.

    Args:
        manager: The :class:`MemoryManager` instance.
    """
    memories = get_cached_memories(manager)
    categories = extract_categories(memories)

    toolbar = render_sort_filter_toolbar(
        toolbar_key="dashboard_all",
        categories=categories,
        show_search=True,
    )
    filtered = apply_sort_filter(
        memories,
        sort_by=toolbar["sort_by"],
        category=toolbar["category"],
        search=toolbar["search"],
    )

    st.divider()

    # Summary row + select-all / invert.
    col_summary, col_select_all, col_invert = st.columns([3, 1, 1])
    with col_summary:
        st.metric(label="Filtered Memories", value=len(filtered))
    with col_select_all:
        if st.button("Select All (page)", key="dashboard_select_all"):
            set_selected_ids(set(current_page_ids(filtered)))
            st.rerun()
    with col_invert:
        if st.button("Invert (page)", key="dashboard_invert"):
            page_ids = set(current_page_ids(filtered))
            current = get_selected_ids()
            set_selected_ids(page_ids ^ current)
            st.rerun()

    if not filtered:
        render_empty_state(
            icon="🧠",
            title="No memories match",
            hint="Adjust filters or add a new memory.",
        )
        return

    # Pagination.
    page = render_pagination(
        total_items=len(filtered),
        page_size=PAGE_SIZE,
        current_page_key="dashboard_page",
    )
    page_start = (page - 1) * PAGE_SIZE
    page_end = page_start + PAGE_SIZE
    page_items = filtered[page_start:page_end]

    st.divider()

    # Render each memory row.
    selected = get_selected_ids()
    for index, memory in enumerate(page_items):
        _render_memory_row(manager, memory, index, selected)
    set_selected_ids(selected)

    # Batch action bar.
    _render_batch_action_bar(manager, selected)


def _render_memory_row(
    manager: MemoryManager,
    memory: dict[str, Any],
    index: int,
    selected_ids: set[str],
) -> None:
    """Render a single memory row with checkbox, content, and actions.

    Args:
        manager: The :class:`MemoryManager` instance.
        memory: The memory record dict.
        index: The row index (for unique widget keys).
        selected_ids: The live set of selected memory ids (mutated).
    """
    memory_id = memory.get("id", f"unknown_{index}")
    content = memory.get("memory", "")
    created_at = memory.get("created_at")
    updated_at = memory.get("updated_at")
    metadata = memory.get("metadata") or {}
    category = metadata.get("category") or metadata.get("type") or ""
    tags = metadata.get("tags")
    if isinstance(tags, list):
        tags_str = ", ".join(str(t) for t in tags)
    elif isinstance(tags, str):
        tags_str = tags
    else:
        tags_str = ""

    with st.container(border=True):
        col_check, col_body = st.columns([1, 12])
        with col_check:
            checked = st.checkbox(
                "Select",
                value=memory_id in selected_ids,
                key=f"check_{index}_{memory_id}",
                label_visibility="collapsed",
            )
            if checked:
                selected_ids.add(memory_id)
            else:
                selected_ids.discard(memory_id)

        with col_body:
            st.markdown(f"**{content}**")
            meta_parts: list[str] = [f"🆔 `{memory_id}`"]
            if category:
                meta_parts.append(f"🏷️ {category}")
            if tags_str:
                meta_parts.append(f"🔖 {tags_str}")
            if created_at:
                meta_parts.append(f"🕒 created {created_at}")
            if updated_at and updated_at != created_at:
                meta_parts.append(f"✏️ updated {updated_at}")
            st.caption(" · ".join(meta_parts))

            with st.expander("✏️ Edit", expanded=False):
                new_content = st.text_area(
                    "Content",
                    value=content,
                    key=f"edit_content_{index}_{memory_id}",
                    height=80,
                )
                col_cat, col_tags = st.columns(2)
                with col_cat:
                    new_category = st.text_input(
                        "Category",
                        value=category,
                        key=f"edit_category_{index}_{memory_id}",
                    )
                with col_tags:
                    new_tags = st.text_input(
                        "Tags (comma-separated)",
                        value=tags_str,
                        key=f"edit_tags_{index}_{memory_id}",
                    )
                col_save, col_delete = st.columns(2)
                with col_save:
                    if st.button(
                        "💾 Save",
                        key=f"save_{index}_{memory_id}",
                        type="primary",
                        use_container_width=True,
                    ) and new_content.strip():
                        handle_update(
                            manager,
                            memory_id,
                            new_content.strip(),
                            new_category.strip(),
                            new_tags.strip(),
                            memory,
                        )
                with col_delete:
                    if st.button(
                        "🗑️ Delete",
                        key=f"del_{index}_{memory_id}",
                        use_container_width=True,
                    ):
                        handle_delete(manager, memory_id)


def _render_batch_action_bar(
    manager: MemoryManager,
    selected_ids: set[str],
) -> None:
    """Render the batch action bar (delete selected, export selected).

    Args:
        manager: The :class:`MemoryManager` instance.
        selected_ids: The set of currently selected memory ids.
    """
    st.divider()
    col_count, col_delete, col_export = st.columns([2, 1, 1])
    with col_count:
        st.caption(f"**{len(selected_ids)}** selected")
    with col_delete:
        if selected_ids and st.button(
            "🗑️ Delete Selected",
            key="dashboard_batch_delete",
            type="secondary",
            use_container_width=True,
        ):
            result = safe_call(
                manager.delete_memories_batch,
                list(selected_ids),
                error_prefix="Batch delete failed",
            )
            if result is not None:
                payload = result.get("results", {})
                deleted = len(payload.get("deleted", []))
                failed = len(payload.get("failed", []))
                st.toast(
                    f"Deleted {deleted} memory(ies)"
                    + (f", {failed} failed" if failed else ""),
                    icon="🗑️",
                )
                set_selected_ids(set())
                invalidate_cache()
                st.rerun()
    with col_export:
        if selected_ids and st.button(
            "⬇️ Export Selected",
            key="dashboard_batch_export",
            use_container_width=True,
        ):
            memories = get_cached_memories(manager)
            selected_memories = [
                m for m in memories if m.get("id") in selected_ids
            ]
            st.download_button(
                label="⬇️ Download JSON",
                data=_to_json(selected_memories),
                file_name="memories_export.json",
                mime="application/json",
                key="dashboard_export_download",
            )


def _to_json(memories: list[dict[str, Any]]) -> str:
    """Serialize memories to a pretty JSON string.

    Args:
        memories: The memory record list.

    Returns:
        A UTF-8 JSON string.
    """
    import json

    return json.dumps(memories, indent=2, ensure_ascii=False)


__all__ = ["render_all_memories_tab"]
