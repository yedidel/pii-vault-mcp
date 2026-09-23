"""Shared logging setup for the Adapter process."""

from __future__ import annotations

import logging
import os
import sys


def configure_logging() -> None:
    level_name = os.getenv("ADAPTER_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stderr,
        force=True,
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
