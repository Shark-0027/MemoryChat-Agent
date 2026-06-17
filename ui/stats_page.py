"""Statistics page for the MemoryChat-Agent UI.

Renders Memory Analytics: total/today/week/month counts, a Memory Health
Score, category breakdown (pie), daily additions (line), and top tags
(bar). All data is fetched via :meth:`MemoryManager.get_statistics`.
"""

from __future__ import annotations

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from memory.manager import MemoryManager
from memory.types import MemoryStatistics
from ui.components import render_empty_state
from ui.widgets import render_metric_grid, safe_call


def _get_memory_manager() -> MemoryManager:
    """Return the session-scoped MemoryManager, creating it if needed.

    Returns:
        The :class:`MemoryManager` instance for this session.
    """
    if "memory_manager" not in st.session_state:
        st.session_state.memory_manager = MemoryManager()
    return st.session_state.memory_manager


def _compute_health_score(stats: MemoryStatistics) -> int:
    """Compute a 0-100 Memory Health Score from statistics.

    A higher score means a healthier, more active memory store. The score
    rewards total volume (up to 50 points) and recent activity (up to 50
    points for memories created this week).

    Args:
        stats: The :class:`MemoryStatistics` payload.

    Returns:
        An integer score in ``[0, 100]``.
    """
    total = stats.get("total", 0)
    week = stats.get("this_week", 0)

    volume_score = min(total / 50.0, 1.0) * 50
    activity_score = min(week / 10.0, 1.0) * 50
    return int(round(volume_score + activity_score))


def _render_health_header(stats: MemoryStatistics) -> None:
    """Render the top-of-page health score and key metrics.

    Args:
        stats: The :class:`MemoryStatistics` payload.
    """
    score = _compute_health_score(stats)
    last_updated = stats.get("last_updated") or "—"

    col_score, col_total, col_cats, col_recent = st.columns(4)
    with col_score:
        st.metric(label="Memory Health Score", value=f"{score} / 100")
    with col_total:
        st.metric(label="Total Memories", value=stats.get("total", 0))
    with col_cats:
        st.metric(label="Categories", value=len(stats.get("categories", [])))
    with col_recent:
        st.metric(label="Last Update", value=last_updated)

    st.divider()

    render_metric_grid(
        [
            {"label": "Today", "value": stats.get("today", 0)},
            {"label": "This Week", "value": stats.get("this_week", 0)},
            {"label": "This Month", "value": stats.get("this_month", 0)},
            {"label": "Top Tags", "value": len(stats.get("tags", []))},
        ],
        columns=4,
    )
    st.divider()


def _render_category_pie(stats: MemoryStatistics) -> None:
    """Render the category breakdown as a pie chart.

    Args:
        stats: The :class:`MemoryStatistics` payload.
    """
    st.subheader("🏷️ Categories")
    categories = stats.get("categories", [])
    if not categories:
        st.caption("No category data available.")
        return

    labels = [c["category"] for c in categories]
    values = [c["count"] for c in categories]
    fig = px.pie(
        names=labels,
        values=values,
        hole=0.4,
        title="Memory distribution by category",
    )
    fig.update_layout(height=380, margin={"l": 10, "r": 10, "t": 40, "b": 10})
    st.plotly_chart(fig, use_container_width=True)


def _render_daily_line(stats: MemoryStatistics) -> None:
    """Render the 30-day daily additions as a line chart.

    Args:
        stats: The :class:`MemoryStatistics` payload.
    """
    st.subheader("📈 Daily Additions (last 30 days)")
    daily = stats.get("daily_counts", [])
    if not daily:
        st.caption("No daily data available.")
        return

    dates = [d["date"] for d in daily]
    counts = [d["count"] for d in daily]
    fig = go.Figure(
        data=go.Scatter(
            x=dates,
            y=counts,
            mode="lines+markers",
            line={"color": "#4f8cff", "width": 2},
            marker={"size": 5},
            fill="tozeroy",
            fillcolor="rgba(79, 140, 255, 0.12)",
        )
    )
    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="New memories",
        height=320,
        margin={"l": 10, "r": 10, "t": 20, "b": 10},
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_tags_bar(stats: MemoryStatistics) -> None:
    """Render the top tags as a horizontal bar chart.

    Args:
        stats: The :class:`MemoryStatistics` payload.
    """
    st.subheader("🔖 Top Tags")
    tags = stats.get("tags", [])[:10]
    if not tags:
        st.caption("No tag data available.")
        return

    labels = [t["tag"] for t in tags][::-1]
    counts = [t["count"] for t in tags][::-1]
    fig = go.Figure(
        data=go.Bar(
            x=counts,
            y=labels,
            orientation="h",
            marker_color="#22c55e",
        )
    )
    fig.update_layout(
        xaxis_title="Count",
        height=max(280, len(labels) * 28),
        margin={"l": 10, "r": 10, "t": 20, "b": 10},
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_topics_bar(stats: MemoryStatistics) -> None:
    """Render the top categories as a vertical bar chart.

    Args:
        stats: The :class:`MemoryStatistics` payload.
    """
    st.subheader("📊 Top Topics (by category)")
    categories = stats.get("categories", [])[:10]
    if not categories:
        st.caption("No topic data available.")
        return

    labels = [c["category"] for c in categories]
    counts = [c["count"] for c in categories]
    fig = go.Figure(
        data=go.Bar(
            x=labels,
            y=counts,
            marker_color="#a855f7",
        )
    )
    fig.update_layout(
        xaxis_title="Category",
        yaxis_title="Count",
        height=320,
        margin={"l": 10, "r": 10, "t": 20, "b": 10},
    )
    st.plotly_chart(fig, use_container_width=True)


def render_stats_page() -> None:
    """Render the Statistics page."""
    st.header("📊 Statistics")
    st.caption("Memory analytics: volume, activity, categories, and tags.")

    manager = _get_memory_manager()

    stats = safe_call(
        manager.get_statistics,
        error_prefix="Failed to load statistics",
    )
    if stats is None:
        return

    if not isinstance(stats, dict) or stats.get("total", 0) == 0:
        render_empty_state(
            icon="📊",
            title="No statistics yet",
            hint="Start chatting or add memories to see analytics here.",
        )
        return

    _render_health_header(stats)

    col_pie, col_topics = st.columns(2)
    with col_pie:
        _render_category_pie(stats)
    with col_topics:
        _render_topics_bar(stats)

    st.divider()
    _render_daily_line(stats)

    st.divider()
    _render_tags_bar(stats)


__all__ = ["render_stats_page"]
