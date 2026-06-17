"""Batch Operations tab for the Memory Dashboard.

Renders export-all, import-from-JSON, and clear-all controls.
"""

from __future__ import annotations

import json

import streamlit as st

from memory.manager import MemoryManager
from ui.dashboard_helpers import invalidate_cache
from ui.widgets import render_confirmation_dialog, safe_call


def render_batch_tab(manager: MemoryManager) -> None:
    """Render the batch operations tab.

    Args:
        manager: The :class:`MemoryManager` instance.
    """
    st.subheader("📦 Batch Operations")
    st.caption("Export, import, or wipe all memories for the current user.")

    _render_export_section(manager)
    _render_import_section(manager)
    _render_clear_section(manager)


def _render_export_section(manager: MemoryManager) -> None:
    """Render the export-all subsection.

    Args:
        manager: The :class:`MemoryManager` instance.
    """
    with st.expander("⬇️ Export All Memories", expanded=False):
        if st.button("Prepare export", key="dashboard_export_all_btn"):
            memories = safe_call(
                manager.export_memories,
                error_prefix="Export failed",
            )
            if memories is not None:
                st.download_button(
                    label="⬇️ Download JSON",
                    data=json.dumps(memories, indent=2, ensure_ascii=False),
                    file_name="memories_all.json",
                    mime="application/json",
                    key="dashboard_export_all_download",
                )
                st.caption(f"{len(memories)} memory(ies) ready to export.")


def _render_import_section(manager: MemoryManager) -> None:
    """Render the import-from-JSON subsection.

    Args:
        manager: The :class:`MemoryManager` instance.
    """
    with st.expander("⬆️ Import Memories", expanded=False):
        uploaded = st.file_uploader(
            "Upload a JSON file",
            type=["json"],
            key="dashboard_import_uploader",
        )
        if uploaded is None:
            return

        try:
            payload = json.loads(uploaded.getvalue().decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            st.error(f"Invalid JSON file: {exc}")
            return

        if not isinstance(payload, list):
            st.error("JSON root must be a list of memory records.")
            return

        st.caption(f"{len(payload)} record(s) parsed.")
        if st.button("⬆️ Import", type="primary", key="dashboard_import_btn"):
            result = safe_call(
                manager.import_memories,
                payload,
                error_prefix="Import failed",
            )
            if result is not None:
                data = result.get("results", {})
                created = len(data.get("deleted", []))
                failed = len(data.get("failed", []))
                st.toast(
                    f"Imported {created} memor(ies)"
                    + (f", {failed} failed" if failed else ""),
                    icon="⬆️",
                )
                invalidate_cache()
                st.rerun()


def _render_clear_section(manager: MemoryManager) -> None:
    """Render the clear-all subsection with confirmation.

    Args:
        manager: The :class:`MemoryManager` instance.
    """
    with st.expander("🧹 Clear All Memories", expanded=False):
        st.warning(
            "This deletes **all** memories for the current user. "
            "This action cannot be undone."
        )
        confirmed = render_confirmation_dialog(
            dialog_key="dashboard_clear_all",
            title="Clear all memories?",
            message="Every memory for the current user will be permanently deleted.",
            confirm_label="Yes, clear all",
            danger=True,
        )
        if confirmed:
            safe_call(
                manager.clear_memory,
                success_message="All memories cleared",
                error_prefix="Clear failed",
            )
            invalidate_cache()
            st.rerun()


__all__ = ["render_batch_tab"]
