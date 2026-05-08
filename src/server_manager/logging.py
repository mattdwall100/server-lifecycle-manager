"""Core logging logic and configuration."""

import logging

from .config import get_LM_settings

settings = get_LM_settings()

logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="[%(asctime)s][%(name)s][%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the module name."""
    return logging.getLogger(name)
