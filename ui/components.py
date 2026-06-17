"""Reusable UI components for MemoryChat-Agent.

This module hosts shared Streamlit widgets used across multiple pages, such as
the status bar, message bubbles, and memory cards.

This module is a stub; the full implementation arrives in a later phase.
"""

from __future__ import annotations


def render_status_bar() -> None:
    """Render the global status bar.

    Shows connection health and the active model configuration. Implementation
    arrives in the next phase.
    """
    import streamlit as st

    st.sidebar.divider()
    st.sidebar.caption("Status bar — implemented in the next phase.")
