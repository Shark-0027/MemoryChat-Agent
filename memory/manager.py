"""Long-term memory manager backed by mem0.

This module provides :class:`MemoryManager`, a typed, UI-independent wrapper
around the mem0 :class:`mem0.Memory` client. All Agent layers that need
long-term memory must go through this manager — never call mem0 directly.

The manager:

* Lazily initializes the mem0 client on first use.
* Builds the mem0 config dict from :data:`config.settings` (no hardcoded
  keys, models, or paths).
* Translates low-level mem0 exceptions into the
  :mod:`memory.exceptions` hierarchy with contextual messages.
* Logs every operation at INFO/DEBUG level via Rich.

Example:
    >>> from memory.manager import MemoryManager
    >>> mgr = MemoryManager()
    >>> mgr.add_memory("I prefer dark mode.", user_id="alice")
    >>> results = mgr.search_memory("UI preferences", user_id="alice")
    >>> [r["memory"] for r in results["results"]]
    ['Prefers dark mode']
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from config import settings
from memory.exceptions import (
    MemoryConfigError,
    MemoryError,
    MemoryInitializationError,
    MemoryNotFoundError,
    MemoryOperationError,
)
from memory.types import (
    BatchDeleteResponse,
    MemoryAddResponse,
    MemoryListResponse,
    MemoryRecord,
    MemorySearchResponse,
    MemoryStatistics,
    MessageResponse,
)
from utils.logger import get_logger

logger: logging.Logger = get_logger(__name__)

# Type alias for the lazily-initialized mem0 Memory client.
MemoryClient = Any


class MemoryManager:
    """Manage long-term memories via mem0.

    The manager is the single entry point for all memory operations in the
    application. It encapsulates client construction, configuration, error
    translation, and logging.

    Attributes:
        _client: The lazily-initialized mem0 :class:`Memory` instance.
        _user_id: Default user id used when a method is called without an
            explicit ``user_id`` argument.
    """

    def __init__(self, user_id: str | None = None) -> None:
        """Initialize the manager without connecting to mem0 yet.

        Args:
            user_id: Optional default user id. If ``None``, falls back to
                :attr:`config.settings.mem0_default_user_id`.
        """
        self._client: MemoryClient | None = None
        self._user_id: str = user_id or settings.mem0_default_user_id

    # ------------------------------------------------------------------ #
    # Public properties
    # ------------------------------------------------------------------ #
    @property
    def client(self) -> MemoryClient:
        """Return the mem0 client, initializing it on first access.

        Returns:
            The initialized mem0 :class:`Memory` instance.

        Raises:
            MemoryInitializationError: If the client cannot be initialized.
        """
        if self._client is None:
            self._client = self._init_client()
        return self._client

    @property
    def default_user_id(self) -> str:
        """Return the default user id used by this manager.

        Returns:
            The default user id string.
        """
        return self._user_id

    # ------------------------------------------------------------------ #
    # Client initialization
    # ------------------------------------------------------------------ #
    def _build_config(self) -> dict[str, Any]:
        """Build the mem0 config dict from application settings.

        Returns:
            A config dict suitable for :meth:`mem0.Memory.from_config`.

        Raises:
            MemoryConfigError: If the OpenAI API key is not configured.
        """
        if not settings.is_configured:
            raise MemoryConfigError(
                "OPENAI_API_KEY is not configured. Set it in .env before using memory."
            )

        vector_store_path: Path = settings.mem0_vector_store_path
        vector_store_path.mkdir(parents=True, exist_ok=True)

        api_key: str = settings.openai_api_key.get_secret_value()

        return {
            "vector_store": {
                "provider": settings.mem0_vector_store,
                "config": {
                    "collection_name": settings.mem0_collection_name,
                    "path": str(vector_store_path),
                },
            },
            "llm": {
                "provider": settings.mem0_llm_provider,
                "config": {
                    "model": settings.openai_model,
                    "api_key": api_key,
                    "openai_base_url": settings.openai_base_url,
                    "temperature": 0.1,
                    "max_tokens": 2000,
                },
            },
            "embedder": {
                "provider": settings.mem0_embedder_provider,
                "config": {
                    "model": settings.openai_embedding_model,
                    "api_key": api_key,
                    "openai_base_url": settings.openai_base_url,
                },
            },
        }

    def _init_client(self) -> MemoryClient:
        """Initialize and return the mem0 Memory client.

        Returns:
            The configured mem0 :class:`Memory` instance.

        Raises:
            MemoryInitializationError: If initialization fails for any reason.
        """
        try:
            from mem0 import Memory
        except ImportError as exc:  # pragma: no cover - dependency is declared
            raise MemoryInitializationError(
                "mem0ai is not installed. Run `uv sync` to install dependencies."
            ) from exc

        try:
            config = self._build_config()
            logger.info(
                "Initializing mem0 client (vector_store=%s, collection=%s, path=%s)",
                settings.mem0_vector_store,
                settings.mem0_collection_name,
                settings.mem0_vector_store_path,
            )
            client = Memory.from_config(config)
            logger.info("mem0 client initialized successfully")
            return client
        except MemoryConfigError:
            raise
        except Exception as exc:
            raise MemoryInitializationError(
                f"Failed to initialize mem0 client: {exc}"
            ) from exc

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _resolve_user_id(self, user_id: str | None) -> str:
        """Return the effective user id for an operation.

        Args:
            user_id: The caller-provided user id, or ``None`` to use the
                manager default.

        Returns:
            The resolved user id string.
        """
        return user_id or self._user_id

    # ------------------------------------------------------------------ #
    # Public API — CRUD + search
    # ------------------------------------------------------------------ #
    def add_memory(
        self,
        messages: str | list[dict[str, str]],
        user_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        infer: bool = True,
    ) -> MemoryAddResponse:
        """Add messages to memory, letting mem0 extract facts automatically.

        Args:
            messages: A string, a single message dict (``role``/``content``),
                or a list of message dicts to memorize.
            user_id: The user identifier to scope the memories. If ``None``,
                uses the manager's default user id.
            metadata: Optional metadata to attach to the stored memories.
            infer: If ``True`` (default), use the LLM to extract facts from
                the messages. If ``False``, store the raw message text.

        Returns:
            A dict with a ``"results"`` key listing the created memories.

        Raises:
            MemoryOperationError: If the underlying mem0 ``add`` call fails.
        """
        uid = self._resolve_user_id(user_id)
        logger.info("Adding memory for user=%s (infer=%s)", uid, infer)
        logger.debug("Messages: %s", messages)

        try:
            response: MemoryAddResponse = self.client.add(
                messages,
                user_id=uid,
                metadata=metadata,
                infer=infer,
            )
        except Exception as exc:
            raise MemoryOperationError(
                f"Failed to add memory for user '{uid}': {exc}"
            ) from exc

        results = response.get("results", [])
        logger.info("Memory add completed: %d item(s) created", len(results))
        return response

    def search_memory(
        self,
        query: str,
        user_id: str | None = None,
        limit: int = 5,
        threshold: float = 0.1,
    ) -> MemorySearchResponse:
        """Retrieve the most relevant memories for a query.

        Args:
            query: The natural-language query to search memories with.
            user_id: The user identifier to scope the search. If ``None``,
                uses the manager's default user id.
            limit: Maximum number of memories to return.
            threshold: Minimum similarity score in ``[0, 1]``.

        Returns:
            A dict with a ``"results"`` key listing matching memories, each
            including a ``score`` field.

        Raises:
            MemoryOperationError: If the underlying mem0 ``search`` call fails.
        """
        uid = self._resolve_user_id(user_id)
        logger.info(
            "Searching memory for user=%s (query=%r, limit=%d, threshold=%.2f)",
            uid,
            query,
            limit,
            threshold,
        )

        try:
            response: MemorySearchResponse = self.client.search(
                query,
                filters={"user_id": uid},
                top_k=limit,
                threshold=threshold,
            )
        except Exception as exc:
            raise MemoryOperationError(
                f"Failed to search memory for user '{uid}': {exc}"
            ) from exc

        results = response.get("results", [])
        logger.info("Memory search completed: %d match(es)", len(results))
        return response

    def list_memory(
        self,
        user_id: str | None = None,
        limit: int = 100,
    ) -> MemoryListResponse:
        """Return all memories for a user.

        Args:
            user_id: The user identifier. If ``None``, uses the manager's
                default user id.
            limit: Maximum number of memories to return.

        Returns:
            A dict with a ``"results"`` key listing the user's memories.
            Items do **not** include a ``score`` field.

        Raises:
            MemoryOperationError: If the underlying mem0 ``get_all`` call fails.
        """
        uid = self._resolve_user_id(user_id)
        logger.info("Listing memory for user=%s (limit=%d)", uid, limit)

        try:
            response: MemoryListResponse = self.client.get_all(
                filters={"user_id": uid},
                top_k=limit,
            )
        except Exception as exc:
            raise MemoryOperationError(
                f"Failed to list memory for user '{uid}': {exc}"
            ) from exc

        results = response.get("results", [])
        logger.info("Memory list completed: %d item(s)", len(results))
        return response

    def get_memory(self, memory_id: str) -> MemoryRecord:
        """Return a single memory by id.

        Args:
            memory_id: The unique identifier of the memory.

        Returns:
            The memory record dict.

        Raises:
            MemoryNotFoundError: If no memory exists with the given id.
            MemoryOperationError: If the underlying mem0 ``get`` call fails.
        """
        logger.info("Fetching memory id=%s", memory_id)

        try:
            response: MemoryRecord | None = self.client.get(memory_id)
        except Exception as exc:
            raise MemoryOperationError(
                f"Failed to get memory '{memory_id}': {exc}"
            ) from exc

        if response is None:
            raise MemoryNotFoundError(f"Memory '{memory_id}' does not exist.")

        logger.debug("Memory fetched: %s", response.get("memory"))
        return response

    def update_memory(
        self,
        memory_id: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> MessageResponse:
        """Update the content of an existing memory.

        Args:
            memory_id: The unique identifier of the memory to update.
            content: The new memory content text.
            metadata: Optional new metadata to attach.

        Returns:
            A dict with a ``"message"`` key confirming the update.

        Raises:
            MemoryOperationError: If the underlying mem0 ``update`` call fails.
        """
        logger.info("Updating memory id=%s", memory_id)
        logger.debug("New content: %s", content)

        try:
            response: MessageResponse = self.client.update(
                memory_id,
                content,
                metadata=metadata,
            )
        except Exception as exc:
            raise MemoryOperationError(
                f"Failed to update memory '{memory_id}': {exc}"
            ) from exc

        logger.info("Memory updated: %s", memory_id)
        return response

    def delete_memory(self, memory_id: str) -> MessageResponse:
        """Delete a single memory by id.

        Args:
            memory_id: The unique identifier of the memory to delete.

        Returns:
            A dict with a ``"message"`` key confirming the deletion.

        Raises:
            MemoryNotFoundError: If the memory does not exist.
            MemoryOperationError: If the underlying mem0 ``delete`` call fails.
        """
        logger.info("Deleting memory id=%s", memory_id)

        try:
            response: MessageResponse = self.client.delete(memory_id)
        except ValueError as exc:
            # mem0 raises ValueError when the memory_id does not exist.
            raise MemoryNotFoundError(
                f"Cannot delete memory '{memory_id}': it does not exist."
            ) from exc
        except Exception as exc:
            raise MemoryOperationError(
                f"Failed to delete memory '{memory_id}': {exc}"
            ) from exc

        logger.info("Memory deleted: %s", memory_id)
        return response

    def clear_memory(self, user_id: str | None = None) -> MessageResponse:
        """Delete all memories for a user.

        Args:
            user_id: The user identifier whose memories should be cleared.
                If ``None``, uses the manager's default user id.

        Returns:
            A dict with a ``"message"`` key confirming the deletion.

        Raises:
            MemoryOperationError: If the underlying mem0 ``delete_all`` call
                fails.
        """
        uid = self._resolve_user_id(user_id)
        logger.warning("Clearing ALL memories for user=%s", uid)

        try:
            response: MessageResponse = self.client.delete_all(user_id=uid)
        except Exception as exc:
            raise MemoryOperationError(
                f"Failed to clear memory for user '{uid}': {exc}"
            ) from exc

        logger.info("All memories cleared for user=%s", uid)
        return response

    # ------------------------------------------------------------------ #
    # Public API — Batch operations & statistics
    # ------------------------------------------------------------------ #
    def delete_memories_batch(
        self,
        memory_ids: list[str],
    ) -> BatchDeleteResponse:
        """Delete multiple memories by id, collecting per-item failures.

        Unlike :meth:`clear_memory` (which wipes everything for a user),
        this method deletes a specific set of memory ids. Failures for
        individual ids (e.g. not found) are collected rather than raised,
        so the caller can see which deletions succeeded and which failed.

        Args:
            memory_ids: The list of memory ids to delete.

        Returns:
            A dict with a ``"results"`` key containing ``deleted`` and
            ``failed`` lists.
        """
        logger.info("Batch deleting %d memory id(s)", len(memory_ids))

        deleted: list[str] = []
        failed: list[dict[str, str]] = []

        for mid in memory_ids:
            try:
                self.delete_memory(mid)
                deleted.append(mid)
            except MemoryNotFoundError as exc:
                failed.append({"id": mid, "error": str(exc)})
            except MemoryError as exc:
                failed.append({"id": mid, "error": str(exc)})

        logger.info(
            "Batch delete completed: %d deleted, %d failed",
            len(deleted),
            len(failed),
        )
        return {"results": {"deleted": deleted, "failed": failed}}

    def get_statistics(
        self,
        user_id: str | None = None,
    ) -> MemoryStatistics:
        """Aggregate statistics over a user's memory store.

        Args:
            user_id: The user identifier. If ``None``, uses the manager's
                default user id.

        Returns:
            A :class:`memory.types.MemoryStatistics` dict with total/today/
            this_week/this_month counts, category/tag breakdowns, daily
            counts for the last 30 days, and the last-updated timestamp.

        Raises:
            MemoryOperationError: If the underlying list operation fails.
        """
        from memory.stats import aggregate_statistics

        uid = self._resolve_user_id(user_id)
        logger.info("Computing statistics for user=%s", uid)

        response = self.list_memory(user_id=uid, limit=10000)
        memories: list[MemoryRecord] = response.get("results", [])
        return aggregate_statistics(memories)

    def export_memories(
        self,
        user_id: str | None = None,
    ) -> list[MemoryRecord]:
        """Export all memories for a user as a JSON-serializable list.

        Args:
            user_id: The user identifier. If ``None``, uses the manager's
                default user id.

        Returns:
            A list of memory record dicts suitable for JSON serialization.

        Raises:
            MemoryOperationError: If the underlying list operation fails.
        """
        uid = self._resolve_user_id(user_id)
        logger.info("Exporting memories for user=%s", uid)

        response = self.list_memory(user_id=uid, limit=10000)
        memories: list[MemoryRecord] = response.get("results", [])
        logger.info("Exported %d memory record(s)", len(memories))
        return memories

    def import_memories(
        self,
        memories: list[dict[str, Any]],
        user_id: str | None = None,
    ) -> BatchDeleteResponse:
        """Import memories from a list of record dicts.

        Each record's ``memory`` text is re-added via :meth:`add_memory`
        with ``infer=False`` (raw storage, no LLM extraction) so the import
        is deterministic and does not require API calls beyond embeddings.

        Args:
            memories: The list of memory record dicts (must each contain a
                ``memory`` key).
            user_id: The user identifier to scope the import. If ``None``,
                uses the manager's default user id.

        Returns:
            A dict with a ``"results"`` key containing ``deleted`` (here,
            the ids of newly created memories) and ``failed`` lists.
        """
        uid = self._resolve_user_id(user_id)
        logger.info("Importing %d memory record(s) for user=%s", len(memories), uid)

        created: list[str] = []
        failed: list[dict[str, str]] = []

        for index, record in enumerate(memories):
            content = record.get("memory") or record.get("content")
            if not content or not str(content).strip():
                failed.append({"id": f"index:{index}", "error": "empty content"})
                continue
            metadata = record.get("metadata")
            try:
                response = self.add_memory(
                    messages=str(content).strip(),
                    user_id=uid,
                    metadata=metadata,
                    infer=False,
                )
                for item in response.get("results", []):
                    new_id = item.get("id")
                    if new_id:
                        created.append(new_id)
            except MemoryError as exc:
                failed.append({"id": f"index:{index}", "error": str(exc)})

        logger.info(
            "Import completed: %d created, %d failed",
            len(created),
            len(failed),
        )
        return {"results": {"deleted": created, "failed": failed}}

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #
    def close(self) -> None:
        """Release resources held by the mem0 client.

        Safe to call multiple times. After closing, the next memory operation
        will re-initialize the client.
        """
        if self._client is not None:
            try:
                self._client.close()
                logger.info("mem0 client closed")
            except Exception as exc:  # pragma: no cover - best-effort cleanup
                logger.warning("Error closing mem0 client: %s", exc)
            finally:
                self._client = None
