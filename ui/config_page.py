"""Config page for the MemoryChat-Agent UI.

Renders a read-only view of the application's configuration: the active
LLM model, base URL, embedding model, memory backend, and storage paths.

This page is display-only — it does not mutate configuration. All values
are read from :data:`config.settings` (which loads from environment
variables / ``.env``). To change configuration, the user edits ``.env``
and restarts the app.
"""

from __future__ import annotations

import streamlit as st

from config import settings


def _render_config_row(label: str, value: str, masked: bool = False) -> None:
    """Render a single configuration row with a label and value.

    Args:
        label: The configuration key name.
        value: The configuration value.
        masked: If ``True``, the value is sensitive (e.g. an API key) and
            is displayed masked.
    """
    col1, col2 = st.columns([1, 2])
    with col1:
        st.markdown(f"**{label}**")
    with col2:
        if masked:
            st.code("••••••••" if value else "(not set)")
        else:
            st.code(value if value else "(not set)")


def render_config_page() -> None:
    """Render the configuration page.

    Displays the LLM, embedding, memory backend, and storage configuration
    in grouped sections. Sensitive values (API keys) are masked.
    """
    st.header("⚙️ Configuration")
    st.caption(
        "Read-only view of the active configuration. "
        "Edit `.env` and restart to change values."
    )

    # --- LLM section ---------------------------------------------------
    st.subheader("🤖 LLM")
    _render_config_row("Provider", settings.mem0_llm_provider)
    _render_config_row("Model", settings.openai_model)
    _render_config_row("Base URL", settings.openai_base_url)
    _render_config_row(
        "API Key",
        settings.openai_api_key.get_secret_value() if settings.is_configured else "",
        masked=True,
    )

    st.divider()

    # --- Embedding section --------------------------------------------
    st.subheader("📐 Embedding")
    _render_config_row("Provider", settings.mem0_embedder_provider)
    _render_config_row("Model", settings.openai_embedding_model)

    st.divider()

    # --- Memory backend section ---------------------------------------
    st.subheader("🧠 Memory Backend")
    _render_config_row("Vector Store", settings.mem0_vector_store)
    _render_config_row("Collection Name", settings.mem0_collection_name)
    _render_config_row(
        "Vector Store Path",
        str(settings.mem0_vector_store_path),
    )
    _render_config_row("Default User ID", settings.mem0_default_user_id)

    st.divider()

    # --- App info section ---------------------------------------------
    st.subheader("📦 Application")
    _render_config_row("App Name", settings.app_name)
    _render_config_row("App Version", settings.app_version)
    _render_config_row("Debug Mode", str(settings.debug))

    st.divider()

    # --- Help / instructions ------------------------------------------
    with st.expander("ℹ️ How to change configuration"):
        st.markdown(
            """
            1. Open the `.env` file in the project root.
            2. Modify the desired values (e.g. `OPENAI_MODEL`, `OPENAI_BASE_URL`).
            3. Save the file.
            4. Restart the app (`uv run streamlit run app/main.py`).

            See `.env.example` for all available configuration options.
            """
        )


__all__ = ["render_config_page"]
