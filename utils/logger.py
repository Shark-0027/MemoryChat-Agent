"""Logging configuration for MemoryChat-Agent.

Provides a :func:`get_logger` factory that returns loggers configured with
Rich's pretty console handler. The log level is driven by
:data:`config.settings.log_level`.

Example:
    >>> from utils.logger import get_logger
    >>> log = get_logger(__name__)
    >>> log.info("Application started")
"""

from __future__ import annotations

import logging
from typing import Final

from rich.logging import RichHandler

from config import settings

_CONFIGURED: Final[bool] = False


def _configure_root_logger() -> None:
    """Configure the root logger with a Rich handler.

    Idempotent: only applies configuration once per process.
    """
    global _CONFIGURED  # noqa: PLW0603
    if _CONFIGURED:
        return

    handler = RichHandler(
        show_time=True,
        show_level=True,
        show_path=False,
        rich_tracebacks=True,
        markup=True,
    )
    handler.setLevel(settings.log_level)

    root = logging.getLogger()
    root.setLevel(settings.log_level)
    root.addHandler(handler)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a configured logger with the given name.

    Args:
        name: The logger name, typically ``__name__`` of the calling module.

    Returns:
        A :class:`logging.Logger` instance emitting Rich-formatted output.
    """
    _configure_root_logger()
    return logging.getLogger(name)
