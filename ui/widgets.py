"""Reusable Streamlit widgets for the MemoryChat-Agent dashboard.

This module hosts higher-level UI primitives that are shared across the
Memory Dashboard, Statistics, and Settings pages:

* :func:`render_pagination` — a Prev / page-number / Next pager.
* :func:`render_sort_filter_toolbar` — sort + filter controls for tables.
* :func:`render_confirmation_dialog` — a two-step confirmation modal.
* :func:`render_metric_grid` — a responsive grid of ``st.metric`` cards.
* :func:`render_loading_spinner` — a contextual loading placeholder.
* :func:`render_toast_or_error` — unified success/error feedback helper.

All widgets are pure rendering functions: they receive data/callbacks and
render UI, without owning business logic.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import streamlit as st


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------
def render_pagination(
    total_items: int,
    page_size: int,
    current_page_key: str,
) -> int:
    """Render a pagination control and return the current 1-based page.

    The current page is stored in ``st.session_state[current_page_key]``
    so it survives reruns. The pager clamps the page to the valid range.

    Args:
        total_items: The total number of items being paginated.
        page_size: The number of items per page.
        current_page_key: The session-state key used to store the page.

    Returns:
        The current 1-based page number.
    """
    if page_size <= 0:
        page_size = 1
    total_pages = max(1, (total_items + page_size - 1) // page_size)

    if current_page_key not in st.session_state:
        st.session_state[current_page_key] = 1
    current = int(st.session_state[current_page_key])
    if current < 1:
        current = 1
    if current > total_pages:
        current = total_pages
    st.session_state[current_page_key] = current

    col_prev, col_info, col_next = st.columns([1, 3, 1])

    with col_prev:
        if st.button("◀ Prev", key=f"{current_page_key}_prev", disabled=current <= 1):
            st.session_state[current_page_key] = current - 1
            st.rerun()

    with col_info:
        start_idx = (current - 1) * page_size + 1
        end_idx = min(current * page_size, total_items)
        st.markdown(
            f"<div style='text-align:center; padding-top:0.4rem; color:#888;'>"
            f"Page <b>{current}</b> / {total_pages} "
            f"&middot; showing <b>{start_idx}-{end_idx}</b> of {total_items}"
            f"</div>",
            unsafe_allow_html=True,
        )

    with col_next:
        if st.button(
            "Next ▶",
            key=f"{current_page_key}_next",
            disabled=current >= total_pages,
        ):
            st.session_state[current_page_key] = current + 1
            st.rerun()

    return current


# ---------------------------------------------------------------------------
# Confirmation dialog
# ---------------------------------------------------------------------------
def render_confirmation_dialog(
    dialog_key: str,
    title: str,
    message: str,
    confirm_label: str = "Confirm",
    danger: bool = False,
) -> bool:
    """Render a two-step confirmation dialog and return whether confirmed.

    Uses ``st.session_state[dialog_key]`` to track the open/closed state.
    The first call renders a "trigger" button; once clicked, the dialog
    body is shown with Confirm/Cancel buttons.

    Args:
        dialog_key: A unique session-state key for this dialog.
        title: The dialog title.
        message: The explanatory message body.
        confirm_label: The confirm button label.
        danger: If ``True``, the confirm button uses the destructive style.

    Returns:
        ``True`` if the user confirmed, ``False`` otherwise.
    """
    state_key = f"{dialog_key}_open"
    if state_key not in st.session_state:
        st.session_state[state_key] = False

    if not st.session_state[state_key]:
        if st.button(
            title,
            key=f"{dialog_key}_trigger",
            type="secondary",
        ):
            st.session_state[state_key] = True
            st.rerun()
        return False

    # Dialog body.
    with st.container(border=True):
        st.markdown(f"**{title}**")
        st.caption(message)
        col_cancel, col_confirm = st.columns(2)
        with col_cancel:
            if st.button("Cancel", key=f"{dialog_key}_cancel", use_container_width=True):
                st.session_state[state_key] = False
                st.rerun()
        with col_confirm:
            if st.button(
                confirm_label,
                key=f"{dialog_key}_confirm",
                type="primary" if not danger else "secondary",
                use_container_width=True,
            ):
                st.session_state[state_key] = False
                return True
    return False


# ---------------------------------------------------------------------------
# Metric grid
# ---------------------------------------------------------------------------
def render_metric_grid(
    metrics: list[dict[str, Any]],
    columns: int = 4,
) -> None:
    """Render a responsive grid of ``st.metric`` cards.

    Args:
        metrics: A list of dicts, each with ``label``, ``value``, and
            optional ``delta`` / ``help`` keys.
        columns: The number of columns per row.
    """
    if columns < 1:
        columns = 1
    for row_start in range(0, len(metrics), columns):
        row = metrics[row_start : row_start + columns]
        cols = st.columns(columns)
        for col, metric in zip(cols, row, strict=False):
            with col:
                st.metric(
                    label=metric.get("label", ""),
                    value=metric.get("value", ""),
                    delta=metric.get("delta"),
                    help=metric.get("help"),
                )


# ---------------------------------------------------------------------------
# Loading & feedback helpers
# ---------------------------------------------------------------------------
def render_loading_spinner(message: str = "Loading…") -> None:
    """Render a centered loading spinner with a caption.

    Args:
        message: The caption text.
    """
    with st.spinner(message):
        st.empty()


def render_toast_or_error(
    success: bool,
    success_message: str,
    error_message: str,
    success_icon: str = "✅",
) -> None:
    """Render a toast on success or an error block on failure.

    Args:
        success: Whether the operation succeeded.
        success_message: The toast text on success.
        error_message: The error text on failure.
        success_icon: The toast icon on success.
    """
    if success:
        st.toast(success_message, icon=success_icon)
    else:
        st.error(error_message)


def safe_call(
    callback: Callable[..., Any],
    *args: Any,
    success_message: str | None = None,
    error_prefix: str = "Operation failed",
    **kwargs: Any,
) -> Any:
    """Invoke a callback, surfacing errors via st.error and toasts.

    Args:
        callback: The callable to invoke.
        *args: Positional args forwarded to ``callback``.
        success_message: If provided, show a toast on success.
        error_prefix: The prefix for the error message on failure.
        **kwargs: Keyword args forwarded to ``callback``.

    Returns:
        The callback's return value, or ``None`` on failure.
    """
    try:
        result = callback(*args, **kwargs)
    except Exception as exc:  # noqa: BLE001 - UI-layer safety net
        st.error(f"{error_prefix}: {exc}")
        return None
    if success_message:
        st.toast(success_message, icon="✅")
    return result


__all__ = [
    "render_confirmation_dialog",
    "render_loading_spinner",
    "render_metric_grid",
    "render_pagination",
    "render_toast_or_error",
    "safe_call",
]
