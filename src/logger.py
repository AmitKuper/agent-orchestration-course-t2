"""Logging factory that writes simultaneously to console and a log file."""

import logging
from pathlib import Path


def setup_logger(name: str, log_file: Path, level: str = "INFO") -> logging.Logger:
    """Create and return a logger with console and file handlers.

    Attaches handlers to the root ancestor of ``name`` (e.g. 'debate' for
    'debate.orchestrator') so all child loggers — including debate.agent.*
    — automatically inherit the file handler and their WARNING/ERROR messages
    are captured in the log file.

    Args:
        name: Logger name, typically the calling module's __name__.
        log_file: Absolute path to the output log file for this run.
        level: Log level string — DEBUG, INFO, WARNING, or ERROR.

    Returns:
        Named Logger instance for the caller; file output flows via the root.
    """
    numeric_level = getattr(logging, level.upper())
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    # Attach handlers to the shared root ancestor so all debate.* children
    # (debate.orchestrator, debate.agent.Hawk, …) write to the same file.
    root_name = name.split(".")[0]
    root_logger = logging.getLogger(root_name)
    if not root_logger.handlers:
        console = logging.StreamHandler()
        console.setFormatter(fmt)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(fmt)
        root_logger.addHandler(console)
        root_logger.addHandler(file_handler)
    root_logger.setLevel(numeric_level)

    logger = logging.getLogger(name)
    logger.setLevel(numeric_level)
    return logger
