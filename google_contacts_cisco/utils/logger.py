"""Logging utilities.

Provides consistent logging configuration across the application.
"""

import logging
import sys
from typing import Optional

from ..config import settings


def get_logger(name: str) -> logging.Logger:
    """Get logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Only configure if not already configured
    if not logger.handlers:
        logger.setLevel(getattr(logging, settings.log_level.upper()))

        # Console handler
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(getattr(logging, settings.log_level.upper()))

        # Format
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)

        logger.addHandler(handler)

    return logger


def configure_root_logger(
    level: Optional[str] = None,
    format_string: Optional[str] = None,
) -> None:
    """Configure the root logger.

    Args:
        level: Log level (defaults to settings.log_level)
        format_string: Log format string (defaults to standard format)
    """
    level = level or settings.log_level
    default_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    format_string = format_string or default_format

    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=format_string,
        handlers=[logging.StreamHandler(sys.stdout)],
    )

