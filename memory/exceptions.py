"""Custom exceptions for the memory subsystem.

All memory-related errors raised by :class:`memory.manager.MemoryManager`
inherit from :class:`MemoryError`, so callers can catch the full family with
a single ``except MemoryError`` clause while still distinguishing specific
failure modes when needed.
"""

from __future__ import annotations


class MemoryError(Exception):
    """Base exception for all memory-related errors."""


class MemoryConfigError(MemoryError):
    """Raised when the memory subsystem is misconfigured.

    For example: missing API key, invalid vector store path, or an
    unconfigured provider.
    """


class MemoryOperationError(MemoryError):
    """Raised when a memory CRUD/search operation fails.

    Wraps the underlying mem0 / vector-store error with context about which
    operation was attempted.
    """


class MemoryNotFoundError(MemoryError):
    """Raised when a memory is requested by id but does not exist."""


class MemoryInitializationError(MemoryError):
    """Raised when the mem0 client cannot be initialized."""
