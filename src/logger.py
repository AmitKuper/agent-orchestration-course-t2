"""Logging factory that writes simultaneously to console and a log file."""

import logging
from pathlib import Path


def setup_logger(name: str, log_file: Path, level: str = "INFO") -> logging.Logger:
    """Create and return a logger with console and file handlers.

    Args:
        name: Logger name, typically the calling module's __name__.
        log_file: Absolute path to the output log file for this run.
        level: Log level string — DEBUG, INFO, WARNING, or ERROR.

    Returns:
        Configured Logger instance ready for use.
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    console = logging.StreamHandler()
    console.setFormatter(fmt)

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(fmt)

    logger.addHandler(console)
    logger.addHandler(file_handler)
    return logger
