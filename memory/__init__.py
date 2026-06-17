"""Memory management package for MemoryChat-Agent.

Wraps the mem0 library to provide long-term memory capabilities:
automatic memory extraction, semantic retrieval, and CRUD operations.

All Agent layers must access memory through :class:`MemoryManager` — never
call mem0 directly.

Modules:
    manager: The :class:`MemoryManager` that wraps mem0's Memory client.
    exceptions: Custom exception hierarchy for memory errors.
    types: TypedDict definitions for memory operation results.

Example:
    >>> from memory.manager import MemoryManager
    >>> mgr = MemoryManager()
    >>> mgr.add_memory("I like Python.", user_id="alice")
"""

from memory.exceptions import (
    MemoryConfigError,
    MemoryError,
    MemoryInitializationError,
    MemoryNotFoundError,
    MemoryOperationError,
)
from memory.manager import MemoryManager

__all__ = [
    "MemoryManager",
    "MemoryError",
    "MemoryConfigError",
    "MemoryInitializationError",
    "MemoryNotFoundError",
    "MemoryOperationError",
]
