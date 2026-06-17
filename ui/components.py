"""Reusable UI components for MemoryChat-Agent.

This module hosts shared Streamlit widgets used across multiple pages:
the sidebar status panel, chat message bubbles, and memory cards.

All components are pure rendering functions — they receive data and render
it, without owning business logic. State management lives in the page
modules and ``app/main.py``.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from config import settings


# ---------------------------------------------------------------------------
# Sidebar status panel
# ---------------------------------------------------------------------------
def render_sidebar_status(memory_count: int | None = None) -> None:
    """Render the system status panel in the sidebar.

    Shows the API-key configuration status, the active model, the embedding
    model, and the total number of stored memories.

    Args:
        memory_count: The total number of stored memories, or ``None`` if
            the count could not be retrieved.
    """
    st.sidebar.markdown("## 📊 System Status")

    # API key status.
    if settings.is_configured:
        st.sidebar.success("✅ API Key configured", icon="✅")
    else:
        st.sidebar.error("❌ API Key missing", icon="❌")

    # Model info.
    st.sidebar.markdown("**Model**")
    st.sidebar.code(settings.openai_model)
    st.sidebar.markdown("**Embedding**")
    st.sidebar.code(settings.openai_embedding_model)

    # Memory count.
    st.sidebar.markdown("**Memory Count**")
    if memory_count is None:
        st.sidebar.caption("—")
    else:
        st.sidebar.metric(label="Memories", value=memory_count)

    st.sidebar.divider()


# ---------------------------------------------------------------------------
# Sidebar action buttons
# ---------------------------------------------------------------------------
def render_sidebar_actions(
    on_clear_chat: Any | None = None,
    on_clear_memory: Any | None = None,
) -> None:
    """Render the action buttons in the sidebar.

    Args:
        on_clear_chat: A callable invoked when the "Clear Chat" button is
            clicked. If ``None``, the button is not shown.
        on_clear_memory: A callable invoked when the "Clear Memory" button
            is clicked. If ``None``, the button is not shown.
    """
    st.sidebar.markdown("## ⚙️ Actions")

    if on_clear_chat is not None and st.sidebar.button(
        "🗑️ Clear Chat", use_container_width=True
    ):
        on_clear_chat()

    if on_clear_memory is not None and st.sidebar.button(
        "🧹 Clear All Memory",
        use_container_width=True,
        type="secondary",
    ):
        on_clear_memory()

    st.sidebar.divider()


# ---------------------------------------------------------------------------
# Chat message bubbles
# ---------------------------------------------------------------------------
def render_user_message(content: str) -> None:
    """Render a single user message bubble.

    Args:
        content: The user's message text.
    """
    with st.chat_message("user"):
        st.markdown(content)


def render_assistant_message(content: str) -> None:
    """Render a single assistant message bubble.

    Args:
        content: The assistant's reply text.
    """
    with st.chat_message("assistant"):
        st.markdown(content)


def render_assistant_stream(stream: Any) -> str:
    """Render a streaming assistant reply and return the full text.

    Args:
        stream: An iterable of text chunks (e.g. from
            :meth:`ChatAgent.stream_chat`).

    Returns:
        The concatenated full reply text.
    """
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_text = ""
        for chunk in stream:
            full_text += chunk
            placeholder.markdown(full_text + "▌")
        placeholder.markdown(full_text)
    return full_text


# ---------------------------------------------------------------------------
# Memory cards
# ---------------------------------------------------------------------------
def render_memory_card(
    memory: dict[str, Any],
    index: int,
    on_delete: Any | None = None,
    on_update: Any | None = None,
) -> None:
    """Render a single memory card with optional delete/update actions.

    Args:
        memory: The memory record dict (must contain at least ``id`` and
            ``memory`` keys).
        index: The display index of this card (for unique widget keys).
        on_delete: A callable taking the memory id, invoked when the delete
            button is clicked. If ``None``, no delete button is shown.
        on_update: A callable taking the memory id and new content, invoked
            when the update button is clicked. If ``None``, no update
            control is shown.
    """
    memory_id = memory.get("id", "unknown")
    content = memory.get("memory", "")
    created_at = memory.get("created_at")
    score = memory.get("score")

    with st.container(border=True):
        # Header row: content + metadata.
        meta_parts: list[str] = []
        if created_at:
            meta_parts.append(f"🕒 {created_at}")
        if score is not None:
            meta_parts.append(f"🎯 score: {score:.2f}")
        meta_parts.append(f"🆔 `{memory_id}`")

        st.markdown(f"**{content}**")
        st.caption(" · ".join(meta_parts))

        # Update control.
        if on_update is not None:
            with st.expander("✏️ Edit", expanded=False):
                new_content = st.text_area(
                    label="Content",
                    value=content,
                    key=f"edit_{index}_{memory_id}",
                    height=80,
                )
                if st.button(
                    "💾 Save",
                    key=f"save_{index}_{memory_id}",
                    type="primary",
                ) and new_content.strip() and new_content != content:
                    on_update(memory_id, new_content.strip())
                    st.success("Memory updated!")
                    st.rerun()

        # Delete button.
        if on_delete is not None and st.button(
            "🗑️ Delete",
            key=f"del_{index}_{memory_id}",
            type="secondary",
        ):
            on_delete(memory_id)
            st.success("Memory deleted!")
            st.rerun()


# ---------------------------------------------------------------------------
# Empty-state placeholders
# ---------------------------------------------------------------------------
def render_empty_state(icon: str, title: str, hint: str = "") -> None:
    """Render a centered empty-state placeholder.

    Args:
        icon: An emoji icon to display.
        title: The main title text.
        hint: Optional secondary hint text.
    """
    st.markdown(
        f"""
        <div style="
            text-align: center;
            padding: 3rem 1rem;
            color: #888;
        ">
            <div style="font-size: 3rem; margin-bottom: 0.5rem;">{icon}</div>
            <div style="font-size: 1.1rem; font-weight: 500;">{title}</div>
            {f'<div style="font-size: 0.9rem; margin-top: 0.25rem;">{hint}</div>' if hint else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )
