""" README
Console output helpers for engine-level workflows.

Sections:
- shared logger configuration
- terminal messaging helpers
- internal logger tools
"""

from __future__ import annotations

__all__ = [
    "configure_logger",
    "dotted_line_fill",
    "error",
    "exit",
    "lprint",
    "warning",
]

#%% === Libraries ===
import sys
import shutil
import logging

from typing import Any

#%% === General Tools ===

# ---------- Variables ----------
def global_variables() -> dict[str, Any]:
    """
    Return shared configuration values used by engine logger helpers.

    Returns:
        dict[str, Any]: Logger names and default display formatting.
    """

    return {
        "logger_name": "runex.ops.lprint",
        "default_border": "\n" + "=" * 50 + "\n",
    }


VAR = global_variables()


class _BorderedFormatter(logging.Formatter):
    """
    Format terminal log messages with a configurable border.

    Args:
        border (str): Border text to wrap around each message.
    """

    def __init__(self, border: str) -> None:
        """Initialize the formatter with one display border."""

        super().__init__("%(message)s")
        self.border = border

    def format(self, record: logging.LogRecord) -> str:
        """
        Format one log record with a border and log level.

        Args:
            record (logging.LogRecord): Log record to format.

        Returns:
            str: Formatted terminal message.
        """

        base_message = super().format(record)
        return f"{self.border}{record.levelname}: {base_message}{self.border}"


#%% === Messaging Helpers ===
def configure_logger(
    border: str = VAR["default_border"],
    level: int = logging.WARNING,
) -> logging.Logger:
    """
    Configure and return the engine logger used for terminal messages.

    Args:
        border (str): Border shown around each emitted message.
        level (int): Logger level to configure.

    Returns:
        logging.Logger: Configured engine logger.
    """

    logger = logging.getLogger(VAR["logger_name"])
    logger.setLevel(level)
    logger.propagate = False

    if not getattr(logger, "_runex_configured", False):
        handler = logging.StreamHandler()
        logger.handlers.clear()
        logger.addHandler(handler)
        logger._runex_configured = True

    if logger.handlers:
        logger.handlers[0].setFormatter(_BorderedFormatter(border))

    return logger


def lprint(message: str, level: int | str = logging.WARNING) -> None:
    """
    Print one message through the engine logger at the requested level.

    Args:
        message (str): Message text to display.
        level (int | str): Logging level as an integer or standard level name.
    """

    if isinstance(level, str):
        normalized_level = getattr(logging, level.strip().upper(), None)
        if not isinstance(normalized_level, int):
            raise ValueError(f"Unsupported log level: {level}")
    else:
        normalized_level = level

    configure_logger(level=normalized_level).log(normalized_level, message)


def warning(message: str) -> None:
    """
    Print a warning-style message through the engine logger.

    Args:
        message (str): Warning text to display.
    """

    lprint(message, logging.WARNING)


def error(message: str) -> None:
    """
    Print an error-style message through the engine logger.

    Args:
        message (str): Error text to display.
    """

    lprint(message, logging.ERROR)


def exit(message: str, exit_code: int = 1) -> None:
    """
    Print an error message and exit the current process.

    Args:
        message (str): Error text to display before exiting.
        exit_code (int): Process exit code.
    """

    error(f"{message}\n\nExiting the program.")
    sys.exit(exit_code)


def dotted_line_fill(prefix: str, suffix: str) -> str:
    """
    Fill the current terminal width with dots between two text fragments.

    Args:
        prefix (str): Leading text.
        suffix (str): Trailing text.

    Returns:
        str: Combined line padded with dots.
    """

    terminal_width = shutil.get_terminal_size(fallback=(80, 20)).columns
    dots_needed = max(0, terminal_width - len(prefix) - len(suffix))
    return f"{prefix}{'.' * dots_needed}{suffix}"
