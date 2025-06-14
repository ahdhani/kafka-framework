"""
Logging configuration for the Kafka framework.
"""

import logging
import sys


def setup_logging(
    level: int = logging.INFO,
    log_format: str | None = None,
    log_file: str | None = None,
) -> None:
    """
    Setup logging configuration for the Kafka framework.

    Args:
        level: Logging level (default: INFO)
        log_format: Custom log format string (optional)
        log_file: Path to log file (optional)

    Example:
        ```python
        from kafka_framework.utils.logging import setup_logging

        # Basic setup with INFO level
        setup_logging()

        # Setup with DEBUG level and custom format
        setup_logging(
            level=logging.DEBUG,
            log_format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        # Setup with file output
        setup_logging(log_file='kafka_framework.log')
        ```
    """
    if log_format is None:
        log_format = (
            "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s"
        )

    handlers = []

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(log_format))
    handlers.append(console_handler)

    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter(log_format))
        handlers.append(file_handler)

    # Root logger for application code
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    for handler in handlers:
        root_logger.addHandler(handler)
