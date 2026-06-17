"""Config page for the MemoryChat-Agent UI.

Renders the runtime configuration inspector. Users can view the current
settings (with secrets masked) and check the health of each dependency
(API key presence, vector store path, etc.).

This module is a stub; the full implementation arrives in a later phase.
"""

from __future__ import annotations


def render_config_page() -> None:
    """Render the configuration page.

    Displays the current non-secret settings and dependency health status.
    Implementation arrives in the next phase.
    """
    import streamlit as st

    st.header("⚙️ Configuration")
    st.info("The configuration inspector will be implemented in the next phase.")
