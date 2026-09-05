"""Structured logging setup for FailureForge."""

import logging
import sys
import structlog


def configure_logging(level: str = "INFO") -> None:
    """Configure structured logging with structlog."""
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.BoundLogger,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a named logger."""
    return structlog.get_logger(name)
