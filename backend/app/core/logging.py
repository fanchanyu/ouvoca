"""Structured logging configuration.

Use `get_logger(__name__)` in any module to get a configured logger.
Logs go to stdout (Docker/K8s friendly) and rotate to file in production.
"""
import logging
import logging.config
import sys
from typing import Any

_CONFIGURED = False


def setup_logging(level: str = "INFO", json_format: bool = False) -> None:
    """Configure root logger once at startup."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    fmt = (
        '{"ts":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}'
        if json_format
        else "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

    logging.basicConfig(
        level=level,
        format=fmt,
        datefmt="%Y-%m-%dT%H:%M:%S",
        stream=sys.stdout,
        force=True,
    )
    # Tame chatty libraries
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("passlib").setLevel(logging.ERROR)
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    if not _CONFIGURED:
        setup_logging()
    return logging.getLogger(name)
