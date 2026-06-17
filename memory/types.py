"""Typed structures returned by the memory subsystem.

These :class:`typing.TypedDict` definitions mirror the dict shapes produced
by mem0 v2.0.x so the rest of the application can rely on static types
instead of ``dict[str, Any]``.

Note:
    mem0 promotes optional payload fields (``user_id``, ``agent_id``,
    ``run_id``, ``actor_id``, ``role``) to top-level keys when present.
    These are declared in the ``total=False`` base classes so they remain
    optional.
"""

from __future__ import annotations

from typing import Any, Literal, TypedDict


# ---------------------------------------------------------------------------
# Shared optional fields promoted from the vector-store payload by mem0.
# ---------------------------------------------------------------------------
class _PromotedFields(TypedDict, total=False):
    """Optional fields that mem0 promotes from the payload to top level.

    Attributes:
        user_id: The user identifier the memory belongs to.
        agent_id: The agent identifier the memory belongs to.
        run_id: The run identifier the memory belongs to.
        actor_id: The actor that produced the memory (e.g. message author).
        role: The role of the message that produced the memory.
    """

    user_id: str
    agent_id: str
    run_id: str
    actor_id: str | None
    role: str


# ---------------------------------------------------------------------------
# add() result item
# ---------------------------------------------------------------------------
class MemoryAddResult(TypedDict):
    """A single item in the ``results`` list returned by ``add``.

    Attributes:
        id: The unique identifier assigned to the stored memory.
        memory: The extracted fact / memory text.
        event: The event type; in mem0 v2.0.x additive extraction this is
            always ``"ADD"``.
    """

    id: str
    memory: str
    event: Literal["ADD", "UPDATE", "DELETE", "NOOP"]


class MemoryAddResponse(TypedDict):
    """Top-level response shape from ``add``.

    Attributes:
        results: The list of memory items created/updated.
    """

    results: list[MemoryAddResult]


# ---------------------------------------------------------------------------
# search() result item (includes score)
# ---------------------------------------------------------------------------
class MemorySearchResult(_PromotedFields, total=False):
    """A single item in the ``results`` list returned by ``search``.

    Unlike :class:`MemoryListItem`, search results include a ``score``.

    Attributes:
        id: The unique identifier of the memory.
        memory: The memory text.
        hash: MD5 hash of the memory content (may be ``None``).
        score: Similarity score in ``[0, 1]``; higher is more similar.
        created_at: ISO timestamp of creation (may be ``None``).
        updated_at: ISO timestamp of last update (may be ``None``).
        metadata: Additional metadata stored with the memory.
    """

    id: str
    memory: str
    hash: str | None
    score: float
    created_at: str | None
    updated_at: str | None
    metadata: dict[str, Any]


class MemorySearchResponse(TypedDict):
    """Top-level response shape from ``search``.

    Attributes:
        results: The list of matching memory items.
    """

    results: list[MemorySearchResult]


# ---------------------------------------------------------------------------
# get_all() result item (no score)
# ---------------------------------------------------------------------------
class MemoryListItem(_PromotedFields, total=False):
    """A single item in the ``results`` list returned by ``get_all``.

    Attributes:
        id: The unique identifier of the memory.
        memory: The memory text.
        hash: MD5 hash of the memory content (may be ``None``).
        created_at: ISO timestamp of creation (may be ``None``).
        updated_at: ISO timestamp of last update (may be ``None``).
        metadata: Additional metadata stored with the memory.
    """

    id: str
    memory: str
    hash: str | None
    created_at: str | None
    updated_at: str | None
    metadata: dict[str, Any]


class MemoryListResponse(TypedDict):
    """Top-level response shape from ``get_all``.

    Attributes:
        results: The list of stored memory items.
    """

    results: list[MemoryListItem]


# ---------------------------------------------------------------------------
# Single memory (from get())
# ---------------------------------------------------------------------------
class MemoryRecord(_PromotedFields, total=False):
    """A single memory record returned by ``get``.

    Attributes:
        id: The unique identifier of the memory.
        memory: The memory text.
        hash: MD5 hash of the memory content (may be ``None``).
        created_at: ISO timestamp of creation (may be ``None``).
        updated_at: ISO timestamp of last update (may be ``None``).
        metadata: Additional metadata stored with the memory.
    """

    id: str
    memory: str
    hash: str | None
    created_at: str | None
    updated_at: str | None
    metadata: dict[str, Any]


# ---------------------------------------------------------------------------
# Simple message acknowledgment (from update / delete / delete_all)
# ---------------------------------------------------------------------------
class MessageResponse(TypedDict):
    """A simple message acknowledgment response.

    Attributes:
        message: The human-readable status message.
    """

    message: str
